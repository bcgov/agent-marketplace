"""Tests for marketplace companion behavior and published command contracts."""

import importlib.util
import subprocess
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote

import pytest
import yaml

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.dont_write_bytecode = True


def _load(name: str, path: Path):
  """Load one bundled companion helper without making its directory a package."""
  spec = importlib.util.spec_from_file_location(name, path)
  module = importlib.util.module_from_spec(spec)
  assert spec.loader is not None
  spec.loader.exec_module(module)
  return module


finder = _load(
  "find_extension",
  ROOT / "scripts" / "find_extension.py",
)
creator = _load(
  "create_extension",
  ROOT / "scripts" / "create_extension.py",
)


def test_repo_local_marketplace_skills_replace_legacy_meta_skills():
  """Phase 3 exposes marketplace workflows instead of generic authoring helpers."""
  skill_root = ROOT / "skills" / "community"
  names = {path.name for path in skill_root.iterdir() if path.is_dir()}
  assert {"bcgov-find-extension", "bcgov-create-extension"} <= names
  assert {"skill-author", "skill-validator"}.isdisjoint(names)


def test_companion_packages_contain_no_runtime_python():
  """Portable companion packages contain instructions and references only."""
  for name in ["bcgov-find-extension", "bcgov-create-extension"]:
    package = ROOT / ".github" / "skills" / name
    assert not list(package.rglob("*.py"))


def test_companion_guidance_is_self_contained_and_progressively_disclosed():
  """Installed skills load only references shipped inside their own package."""
  skill_root = ROOT / "skills" / "community"
  creator_references = {
    path.name
    for path in (skill_root / "bcgov-create-extension" / "references").iterdir()
  }
  assert creator_references == {
    "writing-agents.md",
    "writing-instructions.md",
    "writing-prompts.md",
    "writing-skills.md",
    "SUBMISSION.md",
  }
  finder_references = {
    path.name for path in (skill_root / "bcgov-find-extension" / "references").iterdir()
  }
  assert finder_references == {"INSTALLATION.md", "THIRD_PARTY.md"}

  for name in ["bcgov-find-extension", "bcgov-create-extension"]:
    package = skill_root / name
    content = "\n".join(
      path.read_text(encoding="utf-8") for path in package.rglob("*.md")
    )
    assert "../references/" not in content
    assert "uv run" not in content
    assert "python scripts/" not in content
    assert "internal: true" not in content


def test_companion_relative_links_stay_inside_installed_package():
  """Every local Markdown reference resolves inside the installed skill folder."""
  import re

  for name in ["bcgov-find-extension", "bcgov-create-extension"]:
    package = (ROOT / "skills" / "community" / name).resolve()
    for document in package.rglob("*.md"):
      content = document.read_text(encoding="utf-8")
      for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", content):
        if "://" in target or target.startswith("#"):
          continue
        referenced = (document.parent / unquote(target.split("#", 1)[0])).resolve()
        assert referenced.is_relative_to(package), f"external package link: {target}"
        assert referenced.is_file(), f"missing package link: {target}"


def test_finder_uses_shared_native_choices_and_remote_source_policy():
  """Finder instructions consume client-tested choices without inventing installers."""
  references = ROOT / "skills" / "community" / "bcgov-find-extension" / "references"
  discovery = (references / "THIRD_PARTY.md").read_text(encoding="utf-8")
  installation = (references / "INSTALLATION.md").read_text(encoding="utf-8")
  assert "approved-discovery-sources" in discovery
  assert "Agent Skills Directory" not in discovery
  assert "install-options" in installation
  assert "SHA-256" in installation
  assert "~/.copilot/skills/<name>/" in installation


def test_search_is_deterministic_and_bounded():
  """Finder returns at most three active matches with stable ID tie-breaking."""
  records = []
  for name in ["zeta-actions", "alpha-actions", "beta-actions", "delta-actions"]:
    records.append(
      {
        "id": f"bcgov-public/{name}",
        "display-name": name,
        "summary": "GitHub Actions workflow guidance.",
        "prerequisites": [],
        "lifecycle": "active",
      }
    )
  result = finder.search({"extensions": records}, "actions")
  assert [item["id"] for item in result] == [
    "bcgov-public/alpha-actions",
    "bcgov-public/beta-actions",
    "bcgov-public/delta-actions",
  ]


def test_search_excludes_quarantined_records():
  """Quarantined packages cannot enter default discovery results."""
  catalog = {
    "extensions": [
      {
        "id": "bcgov-public/github-actions",
        "display-name": "GitHub Actions",
        "summary": "Workflow guidance.",
        "prerequisites": [],
        "lifecycle": "quarantined",
      }
    ]
  }
  assert finder.search(catalog, "github actions") == []


def test_search_can_filter_by_extension_type():
  """Type-specific discovery does not return cross-type matches."""
  catalog = {
    "extensions": [
      {
        "id": "bcgov-public/frontend-skill",
        "display-name": "Frontend skill",
        "summary": "Frontend design guidance.",
        "prerequisites": [],
        "lifecycle": "active",
        "type": "skill",
      },
      {
        "id": "bcgov-public/frontend-prompt",
        "display-name": "Frontend prompt",
        "summary": "Frontend design prompt.",
        "prerequisites": [],
        "lifecycle": "active",
        "type": "prompt",
      },
    ]
  }
  assert [item["id"] for item in finder.search(catalog, "frontend", "prompt")] == [
    "bcgov-public/frontend-prompt"
  ]


def test_search_applies_relevance_floor():
  """A weak, single-summary-token overlap is below the floor and returns nothing."""
  catalog = {
    "extensions": [
      {
        "id": "bcgov-public/openshift-deployment",
        "display-name": "OpenShift deployment",
        "summary": "Deploy workloads to OpenShift with manifests.",
        "prerequisites": ["oc CLI"],
        "lifecycle": "active",
      }
    ]
  }
  # "manifests" hits one summary token (score 4), under the floor, so the finder
  # returns a genuine no-match instead of presenting an unrelated skill.
  assert finder.search(catalog, "manifests") == []
  # A name-token query clears the floor and still resolves.
  assert [item["id"] for item in finder.search(catalog, "openshift")] == [
    "bcgov-public/openshift-deployment"
  ]


def test_current_catalog_failure_never_silently_replays_historical_data(monkeypatch):
  """A failed live fetch cannot restore a withdrawn historical record as current."""
  monkeypatch.setattr(
    finder,
    "_download",
    lambda _url: (_ for _ in ()).throw(finder.FinderError("network unavailable")),
  )
  with pytest.raises(finder.FinderError, match="network unavailable"):
    finder.load_catalog(finder.DEFAULT_CATALOG)


@pytest.mark.parametrize(
  ("extension_type", "directory", "filename"),
  [
    ("skill", "skills", "SKILL.md"),
    ("prompt", "prompts", "demo.prompt.md"),
    ("instructions", "instructions", "demo.instructions.md"),
    ("agent", "agents", "demo.agent.md"),
  ],
)
def test_creator_scaffolds_every_declarative_asset_type(
  tmp_path, extension_type, directory, filename
):
  """Every first-release declarative type gets a canonical package scaffold."""
  args = SimpleNamespace(
    marketplace=tmp_path,
    name="demo",
    extension_type=extension_type,
    description="A test asset.",
    display_name="Demo",
    summary="A demo asset.",
    maintainer=["@bcgov/platform-services"],
    specialty="community",
    support="https://github.com/bcgov/agent-marketplace/issues",
    not_ready_on=["claude-code"],
  )
  result = creator.initialize(args)
  package = tmp_path / directory / "community" / "demo"
  assert result["package"] == str(package)
  assert (package / filename).is_file()
  manifest = yaml.safe_load(
    (package / "bcgov-extension.yaml").read_text(encoding="utf-8")
  )
  assert manifest["compatibility"]["not-ready-on"] == ["claude-code"]


def test_finder_reports_requested_removed_id_without_recommending_it():
  """Exact old ids remain discoverable, but normal searches exclude tombstones."""
  catalog = {
    "extensions": [
      {
        "id": "bcgov-public/old-name",
        "type": "skill",
        "lifecycle": "removed",
        "notice": "Use the replacement",
        "moved-to": "bcgov-public/new-name",
        "display-name": "Old name",
        "summary": "Old skill",
        "prerequisites": [],
      }
    ]
  }
  assert finder.search(catalog, "old-name") == []
  assert finder.search(catalog, "bcgov-public/old-name")[0]["moved-to"] == (
    "bcgov-public/new-name"
  )


@pytest.mark.parametrize("extension_type", ["hook", "mcp"])
def test_creator_keeps_executable_integrations_deferred(tmp_path, extension_type):
  """Executable integrations remain outside the first-release product boundary."""
  args = SimpleNamespace(
    marketplace=tmp_path,
    name="demo",
    extension_type=extension_type,
    specialty="community",
  )
  with pytest.raises(creator.CreateError, match="deferred"):
    creator.initialize(args)


def test_reviewed_install_blocks_reserved_extension_types(tmp_path):
  """A catalog record cannot make an unsupported type installable."""
  args = SimpleNamespace(project=tmp_path, id="bcgov-public/release-prompt", yes=True)
  catalog = {
    "extensions": [
      {
        "id": args.id,
        "type": "prompt",
        "lifecycle": "active",
      }
    ]
  }
  with pytest.raises(finder.FinderError, match="no tested install choice"):
    finder._reviewed_install(args, catalog)


def test_immutable_source_validation_and_archive_paths(monkeypatch, tmp_path):
  """Mutable revisions, traversal, and case-colliding archive paths fail closed."""
  with pytest.raises(finder.FinderError, match="full lowercase commit SHA"):
    finder._github_archive_url("https://github.com/example/repository", "main")

  archive_bytes = BytesIO()
  with zipfile.ZipFile(archive_bytes, "w") as archive:
    archive.writestr("repository-root/skills/demo/SKILL.md", "# Demo\n")
    archive.writestr("repository-root/skills/demo/Notes.md", "first\n")
    archive.writestr("repository-root/skills/demo/notes.md", "second\n")
  monkeypatch.setattr(finder, "_download", lambda _url: archive_bytes.getvalue())
  with pytest.raises(finder.FinderError, match="case-colliding"):
    finder.stage_package(
      "https://github.com/example/repository", "a" * 40, "skills/demo", tmp_path
    )

  traversal_bytes = BytesIO()
  with zipfile.ZipFile(traversal_bytes, "w") as archive:
    archive.writestr("repository-root/skills/demo/SKILL.md", "# Demo\n")
    archive.writestr("repository-root/skills/demo/../escape.md", "escape\n")
  monkeypatch.setattr(finder, "_download", lambda _url: traversal_bytes.getvalue())
  with pytest.raises(finder.FinderError, match="path traversal"):
    finder.stage_package(
      "https://github.com/example/repository", "a" * 40, "skills/demo", tmp_path
    )


def test_creator_public_diff_includes_all_untracked_package_files(tmp_path):
  """New package previews contain full diffs rather than a file-list placeholder."""
  subprocess.run(
    ["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True
  )
  package = tmp_path / "skills" / "community" / "demo"
  package.mkdir(parents=True)
  (package / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
  (package / "bcgov-extension.yaml").write_text("id: demo\n", encoding="utf-8")
  diff = creator._public_diff(tmp_path, "skills/community/demo")
  assert "+++ b/skills/community/demo/SKILL.md" in diff
  assert "+++ b/skills/community/demo/bcgov-extension.yaml" in diff
  assert "+# Demo" in diff
  assert "+id: demo" in diff


def test_creator_scaffolds_a_canonical_security_package(tmp_path):
  """The creator supports the active security specialty as well as community."""
  args = SimpleNamespace(
    marketplace=tmp_path,
    name="security-demo",
    specialty="security",
    description="Creates a security demonstration skill.",
    display_name="Security demo",
    summary="Demonstrates the security specialty package path.",
    maintainer=["@bcgov/platform-services"],
    support="https://github.com/bcgov/agent-marketplace/issues",
  )
  result = creator.initialize(args)
  assert result["package"] == str(tmp_path / "skills" / "security" / "security-demo")
  assert (tmp_path / "skills" / "security" / "security-demo" / "SKILL.md").is_file()


def test_creator_accepts_registry_specialty(tmp_path):
  """New specialty ids become valid authoring choices without editing the CLI."""
  config = tmp_path / "config"
  config.mkdir()
  (config / "specialties.yaml").write_text(
    "schema-version: bcgov-marketplace-specialties/v1alpha1\n"
    "specialties:\n"
    "  - id: platform\n"
    "    display-name: Platform\n"
    "    owner-team: '@bcgov/platform'\n"
    "    description: Platform operations.\n"
    "    review-rule: owning-team\n"
    "    display-flair: Platform\n"
  )
  assert (
    creator._package_dir(tmp_path, "demo", "skill", "platform")
    == tmp_path / "skills" / "platform" / "demo"
  )


def test_catalog_ids_match_hosted_manifests():
  """Generated catalog count and IDs exactly match hosted package manifests."""
  import marketplace

  catalog, _ = marketplace.build_catalog(ROOT)
  types = {directory: kind for kind, directory in creator.TYPE_DIRECTORIES.items()}
  package_ids = {
    f"bcgov-public/{types[asset_type]}/{path.parent.name}"
    for asset_type in ("skills", "prompts", "instructions", "agents")
    for path in (ROOT / asset_type).glob("*/*/bcgov-extension.yaml")
  }
  catalog_ids = {record["id"] for record in catalog["extensions"]}
  assert catalog["count"] == len(package_ids)
  assert catalog_ids == package_ids
