"""Behavioral contracts for minimal Manifests and identity transitions."""

import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml
from test_companions import creator, finder
from test_marketplace import ROOT, _root, _skill, m


def package(root, directory="skills", specialty="community", name="demo", **metadata):
  """Write inert native content and a minimal Manifest."""
  path = root / directory / specialty / name
  path.mkdir(parents=True)
  filename = (
    "SKILL.md"
    if directory == "skills"
    else f"{name}.{m.TYPE_DIRECTORIES[directory]}.md"
  )
  (path / filename).write_text(
    f"---\nname: {name}\ndescription: Useful native summary\n---\n\nContent\n",
    encoding="utf-8",
  )
  (path / m.MANIFEST_NAME).write_text(
    yaml.safe_dump(
      {"maintainers": ["@bcgov/platform"], "capabilities": "none", **metadata}
    ),
    encoding="utf-8",
  )
  return path


def test_four_types_with_same_name_validate_through_cli(tmp_path):
  """Type-qualified identities let a mixed native tree share leaf names."""
  root = _root(tmp_path)
  for directory in ("skills", "instructions", "prompts", "agents"):
    package(root, directory)
  result = subprocess.run(
    [
      sys.executable,
      str(ROOT / "scripts/marketplace.py"),
      "--root",
      str(root),
      "generate",
    ],
    capture_output=True,
    text=True,
    check=False,
  )
  assert result.returncode == 0, result.stderr
  catalog = json.loads((root / "catalog/catalog.json").read_text(encoding="utf-8"))
  assert {item["id"] for item in catalog["extensions"]} == {
    "bcgov-public/skill/demo",
    "bcgov-public/instructions/demo",
    "bcgov-public/prompt/demo",
    "bcgov-public/agent/demo",
  }


def test_same_type_name_is_reserved_across_specialties(tmp_path):
  """A Specialty cannot create a second copy of an existing identity."""
  root = _root(tmp_path)
  package(root)
  package(root, specialty="security")
  with pytest.raises(m.MarketplaceError, match="duplicate extension id"):
    m.build_catalog(root)


@pytest.mark.parametrize("targets", [("missing", None), ("a", None), ("b", "a")])
def test_replacement_graph_rejects_missing_self_and_cycle(tmp_path, targets):
  """Every replacement pointer must terminate in an existing distinct record."""
  root = _root(tmp_path)
  for name, target in zip(("a", "b"), targets, strict=True):
    path = package(
      root,
      name=name,
      lifecycle="removed",
      notice="Retired",
      summary="Old package",
      **({"moved-to": f"bcgov-public/skill/{target}"} if target else {}),
    )
    (path / "SKILL.md").unlink()
  with pytest.raises(m.MarketplaceError, match="moved-to"):
    m.build_catalog(root)


def test_replacement_chain_reports_non_active_terminal_without_install(tmp_path):
  """Following A to B to a quarantined C reports its state without migration."""
  root = _root(tmp_path)
  for name, target in (("a", "b"), ("b", "c")):
    path = package(
      root,
      name=name,
      lifecycle="removed",
      notice="Retired",
      summary="Old package",
      **{"moved-to": f"bcgov-public/skill/{target}"},
    )
    (path / "SKILL.md").unlink()
  package(root, name="c", lifecycle="quarantined", notice="Investigation")
  catalog, _ = m.build_catalog(root)
  record = next(item for item in catalog["extensions"] if item["name"] == "a")
  assert record["replacement"] == {
    "id": "bcgov-public/skill/c",
    "lifecycle": "quarantined",
  }
  assert record["install-options"] == []


@pytest.mark.parametrize("source", ["frontmatter", "manifest"])
def test_summary_values_have_same_validity_and_preserve_full_text(tmp_path, source):
  """Native and overridden summaries share their effective validation limits."""
  root = _root(tmp_path)
  summary = "Useful guidance " * 40
  path = package(root, **({"summary": summary} if source == "manifest" else {}))
  if source == "frontmatter":
    (path / "SKILL.md").write_text(
      f"---\nname: demo\ndescription: {summary}\n---\nContent\n", encoding="utf-8"
    )
    summary = summary.rstrip()
  assert m.build_catalog(root)[0]["extensions"][0]["summary"] == summary


@pytest.mark.parametrize(
  "content, correction",
  [(b"\xff", "UTF-8"), (b"---\nname: [\n---\nBody", "YAML frontmatter")],
)
def test_analyze_controls_native_encoding_and_yaml_errors(
  tmp_path, content, correction
):
  """Malformed native files return file/field/fix errors through the public CLI."""
  root = _root(tmp_path)
  path = package(root)
  (path / "SKILL.md").write_bytes(content)
  result = subprocess.run(
    [
      sys.executable,
      str(ROOT / "scripts/marketplace.py"),
      "--root",
      str(root),
      "analyze",
      str(path),
    ],
    capture_output=True,
    text=True,
    check=False,
  )
  assert result.returncode == 1
  assert "SKILL.md:" in result.stderr and correction in result.stderr
  assert "Traceback" not in result.stderr


def test_creator_preserves_support_and_allows_same_name_in_another_type(tmp_path):
  """Creator records honor explicit overrides and type-qualified uniqueness."""
  root = _root(tmp_path)
  arguments = [
    "init",
    "--marketplace",
    str(root),
    "--name",
    "demo",
    "--description",
    "Useful native summary",
    "--display-name",
    "demo",
    "--summary",
    "Useful native summary",
    "--maintainer",
    "@bcgov/platform",
    "--support",
    "https://example.com/help",
  ]
  assert creator.main(arguments) == 0
  assert creator.main([*arguments, "--extension-type", "prompt"]) == 0
  records = m.build_catalog(root)[0]["extensions"]
  assert {record["support"] for record in records} == {"https://example.com/help"}
  assert {record["id"] for record in records} == {
    "bcgov-public/skill/demo",
    "bcgov-public/prompt/demo",
  }


def commit_base(root):
  """Record inert fixture files as the trusted base without using host settings."""
  for args in (
    ("init",),
    ("add", "."),
    (
      "-c",
      "user.name=Fixture",
      "-c",
      "user.email=fixture@example.com",
      "-c",
      "commit.gpgsign=false",
      "commit",
      "-m",
      "base",
    ),
  ):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
  return subprocess.check_output(
    ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
  ).strip()


def test_validate_base_requires_retained_manifest_without_writing_files(tmp_path):
  """An unpublished trusted-main identity remains reserved after content deletion."""
  root = _root(tmp_path)
  path = package(root)
  package(root, name="survivor")
  base = commit_base(root)
  shutil.rmtree(path)
  with pytest.raises(m.MarketplaceError, match="retained.*Manifest"):
    m.analyze_transitions(root, base)
  assert not path.exists()


@pytest.mark.parametrize(
  "change, expected",
  [
    ("content", "non-active-content"),
    ("restore", "restoration"),
    ("transfer", "specialty-transfer"),
    ("notice", "notice"),
  ],
)
def test_analyze_identifies_reviewed_changes_without_rejecting_valid_state(
  tmp_path, change, expected
):
  """Valid lifecycle and content transitions expose facts for the trusted gate."""
  root = _root(tmp_path)
  path = package(root, lifecycle="quarantined", notice="Investigation")
  base = commit_base(root)
  if change == "content":
    (path / "references").mkdir()
    (path / "references/note.md").write_text("Additional guidance", encoding="utf-8")
  elif change == "transfer":
    destination = root / "skills/security/demo"
    destination.parent.mkdir(parents=True)
    path.rename(destination)
  else:
    manifest_path = path / m.MANIFEST_NAME
    metadata = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    metadata.update(
      {"lifecycle": "active"} if change == "restore" else {"notice": "Updated notice"}
    )
    manifest_path.write_text(yaml.safe_dump(metadata), encoding="utf-8")
  facts = m.analyze_transitions(root, base)
  assert len(facts) == 1
  assert facts[0]["id"] == "bcgov-public/skill/demo"
  assert facts[0]["requires-human-review"] is True
  assert expected in facts[0]["reasons"]


def test_analyze_cli_exposes_content_only_transition(tmp_path):
  """The supported analyze seam exposes trusted-base routing facts for #42."""
  root = _root(tmp_path)
  path = package(root, lifecycle="quarantined", notice="Investigation")
  base = commit_base(root)
  (path / "SKILL.md").write_text(
    "---\nname: demo\ndescription: Edited guidance\n---\nBody\n", encoding="utf-8"
  )
  result = subprocess.run(
    [
      sys.executable,
      str(ROOT / "scripts/marketplace.py"),
      "--root",
      str(root),
      "analyze",
      str(path),
      "--base",
      base,
    ],
    capture_output=True,
    text=True,
    check=False,
  )
  assert result.returncode == 0, result.stderr
  assert json.loads(result.stdout)["transitions"][0]["reasons"] == [
    "non-active-content"
  ]


def test_generate_exports_explicit_legacy_lookup_without_rewriting_snapshot(tmp_path):
  """Only inventoried aliases resolve; unrelated name-only IDs do not guess."""
  root = _root(tmp_path)
  package(root)
  (root / "config/legacy-ids.json").write_text(
    json.dumps({"bcgov-public/demo": "bcgov-public/skill/demo"}), encoding="utf-8"
  )
  m.generate(root)
  catalog = json.loads((root / "catalog/catalog.json").read_text(encoding="utf-8"))
  assert (
    finder.lookup_extension(catalog, "bcgov-public/demo")["id"]
    == "bcgov-public/skill/demo"
  )
  assert finder.lookup_extension(catalog, "bcgov-public/unlisted") is None
  historical = {
    "schema-version": "bcgov-marketplace-catalog/v1alpha1",
    "extensions": [{"id": "bcgov-public/demo"}],
  }
  assert (
    finder.lookup_extension(historical, "bcgov-public/demo")["id"]
    == "bcgov-public/demo"
  )
  assert catalog["extensions"][0]["legacy-ids"] == ["bcgov-public/demo"]


def test_catalogue_emits_current_evidence_without_conflicting_aliases(tmp_path):
  """The v1 producer has one checks, risk and policy-route contract."""
  root = _root(tmp_path)
  package(root)
  record = m.build_catalog(root)[0]["extensions"][0]
  assert {"policy", "review", "route"}.isdisjoint(record)
  assert record["checks"]["content-digest"] == record["content-digest"]
  assert record["policy-route"] == {"type": "community"}
  assert record["risk"] == "low"


@pytest.mark.skipif(os.name == "nt", reason="GitHub Actions Bash runs on Linux")
def test_rename_report_outputs_paths_and_fails_on_git_errors(tmp_path):
  """The actual workflow reports renames and cannot mask pipeline errors."""
  root = _root(tmp_path)
  path = package(root)
  base = commit_base(root)
  destination = root / "skills/security/demo"
  destination.parent.mkdir(parents=True)
  path.rename(destination)
  commit_base(root)
  workflow = yaml.safe_load(
    (ROOT / ".github/workflows/pr.yml").read_text(encoding="utf-8")
  )
  command = next(
    step["run"]
    for step in workflow["jobs"]["lint-tests"]["steps"]
    if step.get("name") == "Flag Extension path renames for review"
  )
  summary = root / "summary.md"
  env = {**os.environ, "BASE_SHA": base, "GITHUB_STEP_SUMMARY": str(summary)}
  result = subprocess.run(
    ["bash", "-c", command],
    cwd=root,
    env=env,
    text=True,
    capture_output=True,
    check=False,
  )
  assert result.returncode == 0 and result.stderr == ""
  assert "skills/community/demo/SKILL.md" in summary.read_text(encoding="utf-8")
  assert "skills/security/demo/SKILL.md" in summary.read_text(encoding="utf-8")
  result = subprocess.run(
    ["bash", "-c", command],
    cwd=root,
    env={**env, "BASE_SHA": "invalid-base"},
    text=True,
    capture_output=True,
    check=False,
  )
  assert result.returncode != 0


def test_real_rename_retains_tombstone_and_routes_both_identities(tmp_path):
  """A name change is a reviewed replacement with a distinct reserved old ID."""
  root = _root(tmp_path)
  path = package(root, name="old")
  base = commit_base(root)
  metadata = yaml.safe_load((path / m.MANIFEST_NAME).read_text(encoding="utf-8"))
  metadata.update(
    {
      "lifecycle": "removed",
      "notice": "Renamed",
      "summary": "Previous guidance",
      "moved-to": "bcgov-public/skill/new",
    }
  )
  (path / m.MANIFEST_NAME).write_text(yaml.safe_dump(metadata), encoding="utf-8")
  (path / "SKILL.md").unlink()
  package(root, name="new")
  facts = {fact["id"]: fact for fact in m.analyze_transitions(root, base)}
  assert set(facts) == {"bcgov-public/skill/old", "bcgov-public/skill/new"}
  assert facts["bcgov-public/skill/old"]["new-identity"] is False
  assert facts["bcgov-public/skill/new"]["new-identity"] is True
  assert all(
    "identity-replacement" in fact["reasons"] and fact["requires-human-review"]
    for fact in facts.values()
  )


def test_hardblocked_bytes_require_fix_or_direct_removal(tmp_path):
  """Quarantine cannot bypass blockers; removal does not re-scan deleted bytes."""
  root = _root(tmp_path)
  path = package(root)
  (path / "SKILL.md").write_text(
    _skill(body="password=abcdefghijklmnop\n"), encoding="utf-8"
  )
  base = commit_base(root)
  metadata = yaml.safe_load((path / m.MANIFEST_NAME).read_text(encoding="utf-8"))
  metadata.update(
    {"lifecycle": "quarantined", "notice": "Incident", "summary": "Previous guidance"}
  )
  (path / m.MANIFEST_NAME).write_text(yaml.safe_dump(metadata), encoding="utf-8")
  with pytest.raises(m.MarketplaceError, match="assigned-secret"):
    m.analyze_transitions(root, base)
  metadata["lifecycle"] = "removed"
  (path / m.MANIFEST_NAME).write_text(yaml.safe_dump(metadata), encoding="utf-8")
  (path / "SKILL.md").unlink()
  facts = m.analyze_transitions(root, base)
  assert facts[0]["requires-human-review"] is True
  assert (path / m.MANIFEST_NAME).is_file()


def test_changed_native_package_without_manifest_fails_transition_validation(tmp_path):
  """Every changed content path is checked even when no Manifest was edited."""
  root = _root(tmp_path)
  package(root)
  base = commit_base(root)
  orphan = root / "prompts/community/new"
  orphan.mkdir(parents=True)
  (orphan / "new.prompt.md").write_text(
    "---\ndescription: New prompt\n---\nBody", encoding="utf-8"
  )
  with pytest.raises(
    m.MarketplaceError, match="Manifest alongside every changed native package"
  ):
    m.analyze_transitions(root, base)


def test_new_manifest_only_removed_identity_requires_review(tmp_path):
  """A newly authored retirement record cannot enter the automatic route."""
  root = _root(tmp_path)
  package(root)
  base = commit_base(root)
  path = package(
    root,
    name="retired",
    lifecycle="removed",
    notice="Previous identity",
    summary="Old guidance",
  )
  (path / "SKILL.md").unlink()
  fact = m.analyze_transitions(root, base)[0]
  assert fact["requires-human-review"] is True
