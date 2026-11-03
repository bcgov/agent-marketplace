"""Behavioral contracts for shared native install choices and explicit placement."""

import copy
import hashlib
import json
import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import find_extension as finder  # noqa: E402
import install_choices as installs  # noqa: E402


def test_skill_choice_preserves_native_directory_at_published_sha(tmp_path):
  """A skill keeps its resources, canonical identity and immutable coordinates."""
  (tmp_path / "SKILL.md").write_text(
    "---\nname: demo\ndescription: Demonstration\n---\n# Demo\n"
  )
  (tmp_path / "references").mkdir()
  (tmp_path / "references" / "notes.md").write_bytes(b"reference\n")
  record = {
    "id": "bcgov-public/skill/demo",
    "type": "skill",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "1234567890abcdef1234567890abcdef12345678",
      "path": "skills/community/demo",
    },
  }
  choice = installs.build_install_choices(record, tmp_path)[0]
  assert choice["source-label"] == "Catalogue source"
  assert choice["source-url"] == (
    "https://github.com/example/marketplace/tree/"
    "1234567890abcdef1234567890abcdef12345678/skills/community/demo"
  )
  assert choice["latest-source"] == {
    "label": "latest source",
    "url": "https://github.com/example/marketplace/tree/main/skills/community/demo",
  }
  assert choice["placements"][1] == {
    "source": "references/notes.md",
    "destination": ".github/skills/demo/references/notes.md",
    "sha256": hashlib.sha256(b"reference\n").hexdigest(),
  }


@pytest.mark.parametrize("kind", ["instructions", "prompt", "agent"])
def test_optional_native_headers_flatten_without_requiring_a_description(
  tmp_path, kind
):
  """Manifest summary cannot become a universal native-header requirement."""
  filename = f"demo.{kind}.md"
  directory = "instructions" if kind == "instructions" else kind + "s"
  (tmp_path / filename).write_bytes(b"# Demo\nUse this guidance.\n")
  record = {
    "id": f"bcgov-public/{kind}/demo",
    "type": kind,
    "lifecycle": "active",
    "summary": "A valid Manifest summary",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": f"{directory}/community/demo",
    },
  }
  choice = installs.build_install_choices(record, tmp_path)[0]
  assert choice["client"] == "VS Code Local"
  assert (
    choice["placements"][0]["destination"]
    == {
      "instructions": ".github/instructions/demo.instructions.md",
      "prompt": ".github/prompts/demo.prompt.md",
      "agent": ".github/agents/demo.agent.md",
    }[kind]
  )
  assert choice["evidence"]["runtime-evaluation"] is False


@pytest.mark.parametrize(
  "kind,filename,destination",
  [
    ("skill", "SKILL.md", ".github/skills/demo/SKILL.md"),
    (
      "instructions",
      "demo.instructions.md",
      ".github/instructions/demo.instructions.md",
    ),
    ("prompt", "demo.prompt.md", ".github/prompts/demo.prompt.md"),
    ("agent", "demo.agent.md", ".github/agents/demo.agent.md"),
  ],
)
def test_explicit_placement_verifies_native_bytes_and_refuses_collisions(
  tmp_path, kind, filename, destination
):
  """Each advertised native layout places real bytes only after explicit action."""
  directory = "instructions" if kind == "instructions" else kind + "s"
  package = tmp_path / "package"
  package.mkdir()
  content = b"---\nname: demo\ndescription: Demo\n---\n# Demo\n"
  (package / filename).write_bytes(content)
  record = {
    "id": f"bcgov-public/{kind}/demo",
    "type": kind,
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": f"{directory}/community/demo",
    },
  }
  choice = installs.build_install_choices(record, package)[0]
  project = tmp_path / "project"
  with pytest.raises(installs.PlacementError, match="explicit"):
    installs.place_choice(choice, package, project)
  assert not project.exists()
  result = installs.place_choice(choice, package, project, confirmed=True)
  assert (project / destination).read_bytes() == content
  assert result["verified"] is True
  with pytest.raises(installs.PlacementError, match="collision"):
    installs.place_choice(choice, package, project, confirmed=True)
  (project / destination).write_bytes(b"tampered\n")
  assert installs.verify_choice(choice, project)[0]["valid"] is False


def test_update_requires_old_bytes_and_explicit_specialty_source_migration(tmp_path):
  """Stable identity does not silently follow a Specialty transfer or local edits."""
  package = tmp_path / "package"
  package.mkdir()
  (package / "demo.prompt.md").write_bytes(b"# Original\n")
  record = {
    "id": "bcgov-public/prompt/demo",
    "type": "prompt",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": "prompts/community/demo",
    },
  }
  old = installs.build_install_choices(record, package)[0]
  project = tmp_path / "project"
  installs.place_choice(old, package, project, confirmed=True)
  (package / "demo.prompt.md").write_bytes(b"# Updated\n")
  record["source"].update({"path": "prompts/security/demo", "revision": "b" * 40})
  new = installs.build_install_choices(record, package)[0]
  with pytest.raises(installs.PlacementError, match="migration"):
    installs.place_choice(new, package, project, confirmed=True, previous=old)
  assert (project / ".github/prompts/demo.prompt.md").read_bytes() == b"# Original\n"
  installs.place_choice(
    new, package, project, confirmed=True, previous=old, allow_migration=True
  )
  assert (project / ".github/prompts/demo.prompt.md").read_bytes() == b"# Updated\n"
  (project / ".github/prompts/demo.prompt.md").write_bytes(b"# Local work\n")
  with pytest.raises(installs.PlacementError, match="changed"):
    installs.place_choice(new, package, project, confirmed=True, previous=new)
  other = copy.deepcopy(new)
  other["extension-id"] = "bcgov-public/agent/demo"
  with pytest.raises(installs.PlacementError):
    installs.place_choice(other, package, project, confirmed=True, previous=new)


def test_remove_uses_selected_hashes_and_preserves_unrelated_guidance(tmp_path):
  """Removal needs consent and refuses to delete a locally edited native file."""
  package = tmp_path / "package"
  package.mkdir()
  (package / "demo.agent.md").write_bytes(b"# Agent\n")
  record = {
    "id": "bcgov-public/agent/demo",
    "type": "agent",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": "agents/community/demo",
    },
  }
  choice = installs.build_install_choices(record, package)[0]
  project = tmp_path / "project"
  installs.place_choice(choice, package, project, confirmed=True)
  neighbor = project / ".github/agents/other.agent.md"
  neighbor.write_bytes(b"keep\n")
  with pytest.raises(installs.PlacementError, match="explicit"):
    installs.remove_choice(choice, project)
  installs.remove_choice(choice, project, confirmed=True)
  assert not (project / ".github/agents/demo.agent.md").exists()
  assert neighbor.read_bytes() == b"keep\n"


def test_finder_verifies_explicit_catalog_bytes_without_receipts(tmp_path, capsys):
  """CLI verification compares the selected file hash and reports tampering."""
  package = tmp_path / "package"
  package.mkdir()
  (package / "demo.prompt.md").write_bytes(b"# Prompt\n")
  record = {
    "id": "bcgov-public/prompt/demo",
    "type": "prompt",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": "prompts/community/demo",
    },
  }
  record["install-options"] = installs.build_install_choices(record, package)
  catalog = {
    "schema-version": "bcgov-marketplace/v1",
    "extensions": [record],
    "legacy-ids": {"bcgov-public/demo": record["id"]},
  }
  catalog_path = tmp_path / "catalog.json"
  catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
  project = tmp_path / "project"
  installs.place_choice(record["install-options"][0], package, project, confirmed=True)
  base = [
    "--catalog",
    str(catalog_path),
    "verify",
    record["id"],
    "--project",
    str(project),
  ]
  assert finder.main(base) == 0
  assert json.loads(capsys.readouterr().out)[0]["valid"] is True
  (project / ".github/prompts/demo.prompt.md").write_bytes(b"changed\n")
  assert finder.main(base) == 1
  assert json.loads(capsys.readouterr().out)[0]["valid"] is False
  base[3] = "bcgov-public/demo"
  assert finder.main(base) == 1
  assert "canonical ID or --allow-alias" in capsys.readouterr().err
  assert not (project / ".github/agent-marketplace").exists()


@pytest.mark.parametrize("lifecycle", ["quarantined", "removed", "draft"])
def test_non_active_moved_records_never_offer_a_choice(tmp_path, lifecycle):
  """A replacement pointer cannot authorize installing a non-active identity."""
  record = {
    "id": "bcgov-public/agent/demo",
    "type": "agent",
    "lifecycle": lifecycle,
    "moved-to": "bcgov-public/agent/new-name",
  }
  assert installs.build_install_choices(record, tmp_path) == []


def test_missing_skill_native_fields_suppress_choice_despite_manifest_summary(tmp_path):
  """A normalized summary does not repair the actual client's skill header."""
  (tmp_path / "SKILL.md").write_bytes(b"# Demo\n")
  record = {
    "id": "bcgov-public/skill/demo",
    "type": "skill",
    "lifecycle": "active",
    "summary": "Valid normalized summary",
  }
  assert installs.build_install_choices(record, tmp_path) == []


def test_flattening_with_untested_resource_references_has_no_action(tmp_path):
  """Single-file guidance with resources needs an explicit tested adaptation."""
  (tmp_path / "demo.prompt.md").write_bytes(b"Read [notes](references/notes.md).\n")
  (tmp_path / "references").mkdir()
  (tmp_path / "references/notes.md").write_bytes(b"Notes\n")
  record = {
    "id": "bcgov-public/prompt/demo",
    "type": "prompt",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": "prompts/community/demo",
    },
  }
  assert installs.build_install_choices(record, tmp_path) == []


def test_skill_global_placement_uses_native_personal_home_and_preserves_scope(tmp_path):
  """The one supported global choice installs under the explicitly selected home."""
  package = tmp_path / "package"
  package.mkdir()
  (package / "SKILL.md").write_bytes(
    b"---\nname: demo\ndescription: Demo\n---\n# Skill\n"
  )
  record = {
    "id": "bcgov-public/skill/demo",
    "type": "skill",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": "skills/community/demo",
    },
  }
  global_choice = next(
    choice
    for choice in installs.build_install_choices(record, package)
    if choice["scope"] == "global"
  )
  assert global_choice["destination"] == ".copilot/skills/demo"
  home = tmp_path / "selected-home"
  result = installs.place_choice(global_choice, package, home, confirmed=True)
  assert result["verified"] is True
  assert (home / ".copilot/skills/demo/SKILL.md").read_bytes().endswith(b"# Skill\n")
  assert not (home / ".github").exists()
  with pytest.raises(installs.PlacementError, match="collision"):
    installs.place_choice(global_choice, package, home, confirmed=True)
  installs.remove_choice(global_choice, home, confirmed=True)
  assert not (home / ".copilot/skills/demo/SKILL.md").exists()
  installs.place_choice(global_choice, package, home, confirmed=True)


@pytest.mark.parametrize(
  "kind,header",
  [
    ("instructions", "applyTo: 42"),
    ("agent", "target: github-copilot"),
    ("agent", "tools: 42"),
    ("prompt", "tools: [42]"),
  ],
)
def test_incompatible_native_client_fields_suppress_only_that_choice(
  tmp_path, kind, header
):
  """Catalogue overrides cannot repair malformed native client configuration."""
  directory = "instructions" if kind == "instructions" else kind + "s"
  (tmp_path / f"demo.{kind}.md").write_text(
    f"---\n{header}\n---\n# Guidance\n", encoding="utf-8"
  )
  record = {
    "id": f"bcgov-public/{kind}/demo",
    "type": kind,
    "lifecycle": "active",
    "summary": "Valid summary",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": f"{directory}/community/demo",
    },
  }
  assert installs.build_install_choices(record, tmp_path) == []


@pytest.mark.parametrize(
  "scope,destination",
  [
    ("project", ".github/skills/demo/SKILL.md"),
    ("global", ".copilot/skills/demo/SKILL.md"),
  ],
)
def test_finder_installs_immutable_archive_and_checks_bytes_at_public_cli(
  tmp_path, monkeypatch, capsys, scope, destination
):
  """Actual archive staging uses the Catalogue inventory order on every platform."""
  package = tmp_path / "package"
  package.mkdir()
  native = b"---\nname: demo\ndescription: Demo\n---\n# Demo\n"
  manifest = b"maintainers: ['@example/team']\ncapabilities: none\n"
  (package / "SKILL.md").write_bytes(native)
  (package / "bcgov-extension.yaml").write_bytes(manifest)
  record = {
    "id": "bcgov-public/skill/demo",
    "type": "skill",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "1234567890abcdef1234567890abcdef12345678",
      "path": "skills/community/demo",
    },
  }
  record["files"] = [
    {
      "path": "bcgov-extension.yaml",
      "sha256": hashlib.sha256(manifest).hexdigest(),
      "size": len(manifest),
    },
    {
      "path": "SKILL.md",
      "sha256": hashlib.sha256(native).hexdigest(),
      "size": len(native),
    },
  ]
  record["content-digest"] = finder.tree_digest(record["files"])
  record["install-options"] = installs.build_install_choices(record, package)
  catalog_path = tmp_path / "catalog.json"
  catalog_path.write_text(
    json.dumps(
      {
        "schema-version": "bcgov-marketplace/v1",
        "version": "catalog-2026.11.03",
        "extensions": [record],
        "legacy-ids": {"bcgov-public/demo": record["id"]},
      }
    ),
    encoding="utf-8",
  )
  archive_bytes = BytesIO()
  with zipfile.ZipFile(archive_bytes, "w") as archive:
    archive.writestr("marketplace-root/skills/community/demo/SKILL.md", native)
    archive.writestr(
      "marketplace-root/skills/community/demo/bcgov-extension.yaml", manifest
    )
  downloads = []

  def download(url):
    """Supply one immutable HTTP boundary fixture without replacing local logic."""
    downloads.append(url)
    return archive_bytes.getvalue()

  monkeypatch.setattr(finder, "_download", download)
  project = tmp_path / "project"
  command = [
    "--catalog",
    str(catalog_path),
    "install",
    "bcgov-public/demo",
    "--project",
    str(project),
    "--yes",
    "--allow-alias",
    "--scope",
    scope,
    "--home",
    str(project),
  ]
  assert finder.main(command) == 0
  assert (project / destination).read_bytes() == native
  assert not (project / ".github/skills/demo/bcgov-extension.yaml").exists()
  assert downloads == [
    "https://github.com/example/marketplace/archive/1234567890abcdef1234567890abcdef12345678.zip"
  ]
  assert '"verified": true' in capsys.readouterr().out
  # Same immutable coordinates with different downloaded bytes must not place.
  archive_bytes = BytesIO()
  with zipfile.ZipFile(archive_bytes, "w") as archive:
    archive.writestr(
      "marketplace-root/skills/community/demo/SKILL.md", native + b"changed\n"
    )
    archive.writestr(
      "marketplace-root/skills/community/demo/bcgov-extension.yaml", manifest
    )
  untouched = tmp_path / "untouched"
  command[5] = str(untouched)
  command[-1] = str(untouched)
  assert finder.main(command) == 1
  assert "downloaded bytes do not match" in capsys.readouterr().err
  assert not untouched.exists()


def test_linked_destination_parent_is_a_collision_before_any_write(tmp_path):
  """Placement refuses symlinks even when they point inside the selected project."""
  package = tmp_path / "package"
  package.mkdir()
  (package / "demo.prompt.md").write_bytes(b"# Demo\n")
  record = {
    "id": "bcgov-public/prompt/demo",
    "type": "prompt",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": "prompts/community/demo",
    },
  }
  choice = installs.build_install_choices(record, package)[0]
  project = tmp_path / "project"
  project.mkdir()
  outside = tmp_path / "outside"
  outside.mkdir()
  try:
    (project / ".github").symlink_to(outside, target_is_directory=True)
  except OSError:
    pytest.skip("host does not permit creating test symbolic links")
  with pytest.raises(installs.PlacementError, match="collision"):
    installs.place_choice(choice, package, project, confirmed=True)
  assert list(outside.iterdir()) == []


def test_update_refuses_hardlinked_native_file_without_changing_other_copy(tmp_path):
  """Explicit replacement cannot modify another path through a hard link."""
  package = tmp_path / "package"
  package.mkdir()
  native = package / "demo.prompt.md"
  native.write_bytes(b"# Old\n")
  record = {
    "id": "bcgov-public/prompt/demo",
    "type": "prompt",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": "prompts/community/demo",
    },
  }
  old = installs.build_install_choices(record, package)[0]
  project = tmp_path / "project"
  installs.place_choice(old, package, project, confirmed=True)
  external = tmp_path / "other-copy.md"
  os.link(project / ".github/prompts/demo.prompt.md", external)
  native.write_bytes(b"# New\n")
  new = installs.build_install_choices(record, package)[0]
  with pytest.raises(installs.PlacementError, match="collision"):
    installs.place_choice(new, package, project, previous=old, confirmed=True)
  assert external.read_bytes() == b"# Old\n"


def test_wrong_type_source_coordinates_cannot_advertise_a_choice(tmp_path):
  """A native filename alone cannot make a mismatched source path usable."""
  (tmp_path / "demo.prompt.md").write_bytes(b"# Demo\n")
  record = {
    "id": "bcgov-public/prompt/demo",
    "type": "prompt",
    "lifecycle": "active",
    "source": {
      "repository": "https://github.com/example/marketplace",
      "revision": "a" * 40,
      "path": "agents/community/demo",
    },
  }
  assert installs.build_install_choices(record, tmp_path) == []
