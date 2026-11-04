"""Finder journeys at the public search, fetch, lookup and placement boundaries."""

import copy
import hashlib
import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import find_extension as finder  # noqa: E402
from install_choices import build_install_choices  # noqa: E402


def record(name, lifecycle="active", **extra):
  """Build a literal search record without inventing installation authority."""
  return {
    "id": f"bcgov-public/skill/{name}",
    "type": "skill",
    "display-name": name,
    "summary": "Repository hardening guidance",
    "prerequisites": [],
    "lifecycle": lifecycle,
    **extra,
  }


def test_direct_legacy_lookup_explains_every_notice_and_terminal_state():
  """An exact retired alias explains A -> B -> C without installing C."""
  catalog = {
    "legacy-ids": {"bcgov-public/old": "bcgov-public/skill/a"},
    "extensions": [
      record("a", "removed", notice="Renamed", **{"moved-to": "bcgov-public/skill/b"}),
      record(
        "b",
        "quarantined",
        notice="Under investigation",
        **{"moved-to": "bcgov-public/skill/c"},
      ),
      record("c", "removed", notice="Unavailable permanently"),
    ],
  }
  assert finder.search(catalog, "hardening") == []
  result = finder.search(catalog, "bcgov-public/old")[0]
  assert result["resolution"]["requested-id"] == "bcgov-public/old"
  assert result["resolution"]["canonical-id"] == "bcgov-public/skill/a"
  assert [step["notice"] for step in result["resolution"]["chain"]] == [
    "Renamed",
    "Under investigation",
    "Unavailable permanently",
  ]
  assert result["resolution"]["terminal"] == {
    "id": "bcgov-public/skill/c",
    "lifecycle": "removed",
  }
  assert result["resolution"]["installable"] is False

  assert finder.lookup_extension(catalog, "old") is None
  loop = copy.deepcopy(catalog)
  loop["extensions"][-1]["moved-to"] = "bcgov-public/skill/a"
  result = finder.search(loop, "bcgov-public/old")[0]
  assert "cycle" in result["resolution"]["error"]
  assert result["resolution"]["installable"] is False


@pytest.mark.parametrize(
  "payload",
  [
    b"not JSON",
    b"[]",
    b'{"schema-version":"bcgov-marketplace/v1","extensions":[{}]}',
    b'{"schema-version":"bcgov-marketplace-catalog/v1alpha1","extensions":[]}',
  ],
)
def test_pages_fetch_rejects_invalid_catalogue_without_fallback(monkeypatch, payload):
  """The HTTP boundary supplies malformed data, never an alternate source."""
  requests = []

  def response(request, timeout):
    """Emulate the public HTTP response rather than internal finder behavior."""
    requests.append(request.full_url)
    stream = BytesIO(payload)
    stream.headers = {}
    return stream

  monkeypatch.setattr(finder.urllib.request, "urlopen", response)
  with pytest.raises(finder.FinderError, match="catalog"):
    finder.load_catalog(finder.DEFAULT_CATALOG)
  assert requests == ["https://bcgov.github.io/agent-marketplace/assets/catalog.json"]


def test_pinned_old_lookup_shows_current_withdrawal_or_unavailable_status(
  tmp_path, monkeypatch, capsys
):
  """Pinned source evidence cannot conceal a newer pull-based withdrawal."""
  old = {"schema-version": "bcgov-marketplace/v1", "extensions": [record("demo")]}
  pinned = tmp_path / "old.json"
  pinned.write_text(json.dumps(old))
  current = copy.deepcopy(old)
  current["extensions"][0].update(lifecycle="removed", notice="Credential incident")

  def response(request, timeout):
    """Supply current Pages data at the HTTP boundary."""
    stream = BytesIO(json.dumps(current).encode())
    stream.headers = {}
    return stream

  monkeypatch.setattr(finder.urllib.request, "urlopen", response)
  command = ["--catalog", str(pinned), "search", "bcgov-public/skill/demo"]
  assert finder.main(command) == 0
  result = json.loads(capsys.readouterr().out)[0]
  assert result["current-status"]["record"]["notice"] == "Credential incident"
  assert result["current-status"]["record"]["lifecycle"] == "removed"
  assert result["resolution"]["installable"] is False
  assert finder.main(["--catalog", str(pinned), "search", "Repository hardening"]) == 0
  assert json.loads(capsys.readouterr().out) == []

  def unavailable(request, timeout):
    """Represent an unreachable live status without altering selected bytes."""
    raise OSError("offline")

  monkeypatch.setattr(finder.urllib.request, "urlopen", unavailable)
  assert finder.main(command) == 0
  result = json.loads(capsys.readouterr().out)[0]
  assert result["current-status"]["available"] is False
  assert "offline" in result["current-status"]["diagnostic"]


def package_fixture(
  tmp_path, kind="skill", revision="a" * 40, specialty="community", suffix=b""
):
  """Serve native bytes and a shared choice through a bounded HTTP fixture."""
  package = tmp_path / ("package-" + revision[0] + specialty)
  package.mkdir()
  filename = "SKILL.md" if kind == "skill" else f"demo.{kind}.md"
  native = b"---\nname: demo\ndescription: Repository hardening\n---\n# Demo\n" + suffix
  manifest = b"maintainers: ['@example/team']\ncapabilities: none\n"
  (package / filename).write_bytes(native)
  (package / "bcgov-extension.yaml").write_bytes(manifest)
  directory = "instructions" if kind == "instructions" else kind + "s"
  item = record(
    "demo",
    type=kind,
    source={
      "repository": "https://github.com/bcgov/agent-marketplace",
      "revision": revision,
      "path": f"{directory}/{specialty}/demo",
    },
  )
  item["id"] = f"bcgov-public/{kind}/demo"
  item["files"] = sorted(
    [
      {
        "path": filename,
        "size": len(native),
        "sha256": hashlib.sha256(native).hexdigest(),
      },
      {
        "path": "bcgov-extension.yaml",
        "size": len(manifest),
        "sha256": hashlib.sha256(manifest).hexdigest(),
      },
    ],
    key=lambda file: file["path"].lower(),
  )
  item["content-digest"] = finder.tree_digest(item["files"])
  item["install-options"] = build_install_choices(item, package)
  catalog = {
    "schema-version": "bcgov-marketplace/v1",
    "release-state": "published",
    "version": "catalog-2026.11.03",
    "extensions": [item],
    "legacy-ids": {"bcgov-public/demo": item["id"]},
  }
  buffer = BytesIO()
  with zipfile.ZipFile(buffer, "w") as archive:
    for name, content in [(filename, native), ("bcgov-extension.yaml", manifest)]:
      archive.writestr(f"marketplace-root/{directory}/{specialty}/demo/{name}", content)
  return catalog, buffer.getvalue(), native


def serve(monkeypatch, catalog, archive, requests):
  """Serve only Pages and the advertised immutable archive at the HTTP boundary."""

  def response(request, timeout):
    """Reject any unadvertised network route instead of hiding fallback requests."""
    url = request.full_url
    requests.append(url)
    assert timeout <= 60
    if url == "https://bcgov.github.io/agent-marketplace/assets/catalog.json":
      payload = json.dumps(catalog).encode()
    else:
      revision = catalog["extensions"][0]["source"]["revision"]
      assert url == f"https://github.com/bcgov/agent-marketplace/archive/{revision}.zip"
      payload = archive
    stream = BytesIO(payload)
    stream.headers = {"Content-Length": str(len(payload))}
    return stream

  monkeypatch.setattr(finder.urllib.request, "urlopen", response)


@pytest.mark.parametrize(
  "kind,scope,destination",
  [
    ("skill", "project", ".github/skills/demo/SKILL.md"),
    ("skill", "global", ".copilot/skills/demo/SKILL.md"),
    ("instructions", "project", ".github/instructions/demo.instructions.md"),
    ("prompt", "project", ".github/prompts/demo.prompt.md"),
    ("agent", "project", ".github/agents/demo.agent.md"),
  ],
)
def test_confirmed_native_cli_placement_for_each_tested_type_and_scope(
  tmp_path, monkeypatch, capsys, kind, scope, destination
):
  """The actual CLI pins, confirms, places and compares each advertised layout."""
  catalog, archive, native = package_fixture(tmp_path, kind)
  requests = []
  serve(monkeypatch, catalog, archive, requests)
  prompts = []

  def confirm(prompt):
    """Capture the exact write plan confirmed by the caller."""
    prompts.append(prompt)
    return "yes"

  monkeypatch.setattr("builtins.input", confirm)
  root = tmp_path / "selected-root"
  command = [
    "install",
    f"bcgov-public/{kind}/demo",
    "--project",
    str(root),
    "--home",
    str(root),
    "--scope",
    scope,
    "--expected-revision",
    "a" * 40,
  ]
  assert finder.main(command) == 0
  assert (root / destination).read_bytes() == native
  assert "a" * 40 in prompts[0] and f"scope={scope}" in prompts[0]
  confirmed_destination = (
    (root / destination).parent if kind == "skill" else root / destination
  )
  assert str(confirmed_destination) in prompts[0]
  output = capsys.readouterr().out
  assert '"installer": "manual"' in output
  assert '"targets-exist": true' in output and '"verified": true' in output
  assert "latest published Catalogue source (full-SHA pin)" in output
  assert finder.main(command) == 1
  assert "collision" in capsys.readouterr().err
  assert (root / destination).read_bytes() == native


def test_previously_confirmed_sha_refuses_a_new_latest_revision(
  tmp_path, monkeypatch, capsys
):
  """A later write cannot silently substitute a newer published source SHA."""
  catalog, archive, _ = package_fixture(tmp_path, revision="b" * 40)
  requests = []
  serve(monkeypatch, catalog, archive, requests)
  root = tmp_path / "untouched"
  assert (
    finder.main(
      [
        "install",
        "bcgov-public/skill/demo",
        "--yes",
        "--project",
        str(root),
        "--expected-revision",
        "a" * 40,
      ]
    )
    == 1
  )
  assert "revision changed" in capsys.readouterr().err
  assert requests == [finder.DEFAULT_CATALOG]
  assert not root.exists()


@pytest.mark.parametrize("lifecycle", ["quarantined", "removed"])
def test_pinned_install_refuses_current_withdrawal_and_keeps_removal_available(
  tmp_path, monkeypatch, capsys, lifecycle
):
  """A current withdrawal blocks old installations while preserving explicit removal."""
  old, archive, _ = package_fixture(tmp_path)
  requests = []
  serve(monkeypatch, old, archive, requests)
  root = tmp_path / "project"
  identity = "bcgov-public/skill/demo"
  assert finder.main(["install", identity, "--yes", "--project", str(root)]) == 0
  capsys.readouterr()
  pinned = tmp_path / "old.json"
  pinned.write_text(json.dumps(old))
  current = copy.deepcopy(old)
  current["extensions"][0].update(lifecycle=lifecycle, notice="Incident withdrawal")
  current["extensions"][0]["install-options"] = []
  requests.clear()
  serve(monkeypatch, current, archive, requests)
  assert (
    finder.main(
      [
        "--catalog",
        str(pinned),
        "install",
        identity,
        "--yes",
        "--project",
        str(tmp_path / "untouched"),
      ]
    )
    == 1
  )
  assert "Incident withdrawal" in capsys.readouterr().err
  assert requests == [finder.DEFAULT_CATALOG]
  assert not (tmp_path / "untouched").exists()
  assert (
    finder.main(
      ["--catalog", str(pinned), "remove", identity, "--yes", "--project", str(root)]
    )
    == 0
  )
  assert not (root / ".github/skills/demo/SKILL.md").exists()


def test_cli_overwrite_requires_matching_old_bytes_and_explicit_source_migration(
  tmp_path, monkeypatch, capsys
):
  """An update confirms its revision, overwrite and source transfer before copying."""
  old, old_archive, old_native = package_fixture(tmp_path)
  old_path = tmp_path / "old.json"
  old_path.write_text(json.dumps(old))
  root = tmp_path / "project"
  identity = "bcgov-public/skill/demo"
  requests = []
  serve(monkeypatch, old, old_archive, requests)
  assert finder.main(["install", identity, "--project", str(root), "--yes"]) == 0
  capsys.readouterr()
  new, archive, new_native = package_fixture(
    tmp_path, revision="b" * 40, specialty="security", suffix=b"Changed\n"
  )
  serve(monkeypatch, new, archive, requests)
  command = [
    "install",
    identity,
    "--project",
    str(root),
    "--previous-catalog",
    str(old_path),
  ]
  prompts = []

  def confirm(prompt):
    """Accept the exact displayed source and overwrite plan."""
    prompts.append(prompt)
    return "yes"

  monkeypatch.setattr("builtins.input", confirm)
  assert finder.main(command) == 1
  assert "migration" in capsys.readouterr().err
  target = root / ".github/skills/demo/SKILL.md"
  assert target.read_bytes() == old_native
  assert finder.main([*command, "--allow-migration"]) == 0
  output = capsys.readouterr().out
  assert '"action": "overwrite"' in output
  assert '"migration-approved": true' in output
  assert "Overwrite" in prompts[-1] and "b" * 40 in prompts[-1]
  assert "migration=True" in prompts[-1]
  assert target.read_bytes() == new_native


@pytest.mark.parametrize(
  "field,value", [("source", []), ("install-options", [{}]), ("files", [{}])]
)
def test_malformed_native_install_evidence_is_a_catalogue_error(tmp_path, field, value):
  """Untrusted schema errors have a diagnostic before native placement is offered."""
  catalog, _, _ = package_fixture(tmp_path)
  catalog["extensions"][0][field] = value
  path = tmp_path / "invalid.json"
  path.write_text(json.dumps(catalog))
  with pytest.raises(finder.FinderError, match="schema"):
    finder.load_catalog(str(path))


def test_explicit_legacy_snapshot_is_inspection_only_with_current_finite_alias(
  tmp_path, monkeypatch, capsys
):
  """The actual pre-v1 asset stays inspectable without reviving legacy installers."""
  historical = Path(__file__).parent / "fixtures/publication/legacy-catalog.json"
  current = {
    "schema-version": "bcgov-marketplace/v1",
    "extensions": [
      record("azure-networking", "removed", notice="Retired old revision")
    ],
    "legacy-ids": {
      "bcgov-public/azure-networking": "bcgov-public/skill/azure-networking"
    },
  }
  requests = []
  serve(monkeypatch, current, b"", requests)
  assert (
    finder.main(
      ["--catalog", str(historical), "search", "bcgov-public/azure-networking"]
    )
    == 0
  )
  result = json.loads(capsys.readouterr().out)[0]
  assert result["id"] == "bcgov-public/azure-networking"
  assert result["resolution"]["canonical-id"] == "bcgov-public/skill/azure-networking"
  assert result["current-status"]["record"]["notice"] == "Retired old revision"
  assert result["historical-inspection-only"] is True
  assert result["install-options"] == []
  untouched = tmp_path / "untouched"
  assert (
    finder.main(
      [
        "--catalog",
        str(historical),
        "install",
        "bcgov-public/azure-networking",
        "--yes",
        "--project",
        str(untouched),
      ]
    )
    == 1
  )
  assert not untouched.exists()


def test_selected_identity_cannot_remove_another_extensions_files(
  tmp_path, monkeypatch, capsys
):
  """Malformed choice evidence cannot redirect a selected native removal."""
  catalog, archive, native = package_fixture(tmp_path)
  requests = []
  serve(monkeypatch, catalog, archive, requests)
  root = tmp_path / "project"
  identity = "bcgov-public/skill/demo"
  assert finder.main(["install", identity, "--yes", "--project", str(root)]) == 0
  capsys.readouterr()
  catalog["extensions"][0]["id"] = "bcgov-public/skill/other"
  catalog["legacy-ids"] = {}
  assert (
    finder.main(["remove", "bcgov-public/skill/other", "--yes", "--project", str(root)])
    == 1
  )
  assert "choice" in capsys.readouterr().err
  assert (root / ".github/skills/demo/SKILL.md").read_bytes() == native


@pytest.mark.parametrize("terminal", ["active", "removed", "loop", "missing"])
def test_direct_chain_cli_never_installs_an_unconfirmed_replacement(
  tmp_path, monkeypatch, capsys, terminal
):
  """Direct retired identities expose finite chains, unavailable ends and bad input."""
  catalog, archive, _ = package_fixture(tmp_path)
  end = catalog["extensions"][0]
  if terminal == "removed":
    end.update(lifecycle="removed", notice="Terminal unavailable")
    end["install-options"] = []
  elif terminal == "loop":
    end["moved-to"] = "bcgov-public/skill/old"
  elif terminal == "missing":
    end["moved-to"] = "bcgov-public/skill/absent"
  catalog["extensions"].extend(
    [
      record(
        "old",
        "removed",
        notice="Old notice",
        **{"moved-to": "bcgov-public/skill/middle"},
      ),
      record(
        "middle",
        "quarantined",
        notice="Intermediate notice",
        **{"moved-to": "bcgov-public/skill/demo"},
      ),
    ]
  )
  catalog["legacy-ids"]["bcgov-public/old"] = "bcgov-public/skill/old"
  requests = []
  serve(monkeypatch, catalog, archive, requests)
  assert finder.main(["search", "bcgov-public/old"]) == 0
  result = json.loads(capsys.readouterr().out)[0]
  assert [item["id"] for item in result["resolution"]["chain"]] == [
    "bcgov-public/skill/old",
    "bcgov-public/skill/middle",
    "bcgov-public/skill/demo",
  ]
  assert result["resolution"]["installable"] is False
  if terminal in {"active", "removed"}:
    assert result["resolution"]["terminal"]["lifecycle"] == terminal
  else:
    assert "error" in result["resolution"]
  assert finder.main(["search", "bcgov-public/skill/does-not-exist"]) == 0
  assert json.loads(capsys.readouterr().out) == []
  untouched = tmp_path / "untouched"
  assert (
    finder.main(
      [
        "install",
        "bcgov-public/old",
        "--allow-alias",
        "--yes",
        "--project",
        str(untouched),
      ]
    )
    == 1
  )
  assert not untouched.exists()
  assert requests == [finder.DEFAULT_CATALOG] * 3


@pytest.mark.parametrize("selection", ["latest", "historical", "preview"])
def test_search_labels_selected_catalogue_separately_from_source_sha(
  tmp_path, monkeypatch, capsys, selection
):
  """A full SHA, published snapshot and source preview retain distinct meanings."""
  catalog, archive, _ = package_fixture(tmp_path)
  if selection == "preview":
    catalog.update({"version": "source", "release-state": "development"})
  requests = []
  serve(monkeypatch, catalog, archive, requests)
  command = ["search", "bcgov-public/skill/demo"]
  if selection != "latest":
    path = tmp_path / "selected.json"
    path.write_text(json.dumps(catalog))
    command = ["--catalog", str(path), *command]
  assert finder.main(command) == 0
  result = json.loads(capsys.readouterr().out)[0]
  expected_label = {
    "latest": "latest published Catalogue source (full-SHA pin)",
    "historical": "selected published snapshot source (full-SHA pin)",
    "preview": "Catalogue source (preview)",
  }[selection]
  assert result["catalogue-selection"]["label"] == expected_label
  assert result["catalogue-selection"]["snapshot"] == catalog["version"]
  assert result["source"]["revision"] == "a" * 40
  assert result["install-options"][0]["latest-source"]["label"] == "latest source"
