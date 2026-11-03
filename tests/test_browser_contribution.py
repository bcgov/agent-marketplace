"""Public browser starter and package-validation contracts."""

import json
import subprocess
import sys

import pytest
import yaml
from test_marketplace import ROOT, _package, _root, m


def starters(root):
  """Build the browser's public data through its command-line interface."""
  result = subprocess.run(
    [
      sys.executable,
      str(ROOT / "scripts/browser_contribution.py"),
      "--root",
      str(root),
    ],
    capture_output=True,
    text=True,
    check=False,
  )
  assert result.returncode == 0, result.stderr
  return json.loads((root / "docs/assets/contribute.json").read_text(encoding="utf-8"))


def test_registry_only_specialty_and_reserved_names_reach_browser(tmp_path):
  """Onboarding requires only registry data; identities stay unique per type."""
  root = _root(tmp_path)
  registry = root / "config/specialties.yaml"
  data = yaml.safe_load(registry.read_text(encoding="utf-8"))
  data["specialties"].append(
    {
      "id": "water",
      "display-name": "Water stewardship",
      "description": "Water guidance.",
      "owner-team": "@bcgov/water",
      "review-rule": "owning-team",
      "display-flair": "Water",
    }
  )
  registry.write_text(yaml.safe_dump(data), encoding="utf-8")
  _package(root, name="reserved")
  data = starters(root)
  assert data["specialties"][0]["id"] == "community"
  assert data["specialties"][-1] == {
    "id": "water",
    "display-name": "Water stewardship",
    "description": "Water guidance.",
    "owner-team": "@bcgov/water",
    "review-rule": "owning-team",
    "display-flair": "Water",
  }
  assert data["reserved"] == ["bcgov-public/skill/reserved"]


def browser_starter(data, kind, specialty="community", name="browser-demo"):
  """Render the browser's exact copyable files using its public JS interface."""
  result = subprocess.run(
    [
      "node",
      "-e",
      "const ui = require(process.argv[1]); "
      "console.log(JSON.stringify(ui.starter(JSON.parse(process.argv[2]), "
      "JSON.parse(process.argv[3]))));",
      str(ROOT / "docs/assets/contribute.js"),
      json.dumps(data),
      json.dumps(
        {
          "type": kind,
          "specialty": specialty,
          "name": name,
          "maintainer": "browser-author",
          "summary": 'Useful guidance: "review" & inspect café.',
          "base": "v1/7-integration",
        }
      ),
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    check=False,
  )
  assert result.returncode == 0, result.stderr
  return json.loads(result.stdout)


@pytest.mark.parametrize("kind", ["skill", "instructions", "prompt", "agent"])
@pytest.mark.parametrize("specialty", ["community", "security"])
def test_browser_two_file_stubs_validate_with_untouched_metadata_defaults(
  tmp_path, kind, specialty
):
  """Copying the filled stubs needs only maintainers and capability declarations."""
  root = _root(tmp_path)
  result = browser_starter(starters(root), kind, specialty)
  assert set(yaml.safe_load(result["manifest"])) == {"maintainers", "capabilities"}
  assert result["nativePath"].endswith(
    "/SKILL.md" if kind == "skill" else f"/browser-demo.{kind}.md"
  )
  for path, text in (
    (result["nativePath"], result["native"]),
    (result["manifestPath"], result["manifest"]),
  ):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
  catalog, _ = m.build_catalog(root)
  assert catalog["extensions"][0]["summary"] == (
    'Useful guidance: "review" & inspect café.'
  )
  if kind == "skill":
    validation = subprocess.run(
      [
        sys.executable,
        str(ROOT / "scripts/validate_skill.py"),
        str(root / result["nativePath"]),
        "--no-duplicates",
      ],
      capture_output=True,
      text=True,
      check=False,
    )
    assert validation.returncode == 0, validation.stdout


@pytest.mark.parametrize("kind", ["skill", "instructions", "prompt", "agent"])
def test_registry_only_specialty_native_content_is_validated(tmp_path, kind):
  """A new registry entry gets native checks, not just a selectable label."""
  root = _root(tmp_path)
  registry = root / "config/specialties.yaml"
  text = registry.read_text(encoding="utf-8")
  registry.write_text(text.replace("security", "water"), encoding="utf-8")
  result = browser_starter(starters(root), kind, "water")
  for path, text in (
    (result["nativePath"], result["native"]),
    (result["manifestPath"], result["manifest"]),
  ):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
  catalog, _ = m.build_catalog(root)
  assert catalog["extensions"][0]["policy-route"]["owner-team"] == "@bcgov/water"
  (root / result["nativePath"]).write_text("---\nname: []\n---\n", encoding="utf-8")
  with pytest.raises(m.MarketplaceError, match="frontmatter|content|summary"):
    m.build_catalog(root)


@pytest.mark.parametrize("missing", ["summary", "manifest"])
def test_missing_browser_fields_give_direct_fixes(tmp_path, missing):
  """The authoritative package check points browser authors to a correction."""
  root = _root(tmp_path)
  result = browser_starter(starters(root), "prompt")
  package = root / result["manifestPath"]
  package.parent.mkdir(parents=True)
  (root / result["nativePath"]).write_text(
    "---\nname: browser-demo\n---\nUseful content\n"
    if missing == "summary"
    else result["native"],
    encoding="utf-8",
  )
  if missing != "manifest":
    package.write_text(result["manifest"], encoding="utf-8")
  validation = subprocess.run(
    [
      sys.executable,
      str(ROOT / "scripts/marketplace.py"),
      "--root",
      str(root),
      "analyze",
      str(package.parent),
    ],
    capture_output=True,
    text=True,
    check=False,
  )
  assert validation.returncode == 1
  assert (
    "add `description:` to the frontmatter or `summary:` to the Manifest"
    if missing == "summary"
    else "Add bcgov-extension.yaml alongside the native file"
  ) in validation.stderr
