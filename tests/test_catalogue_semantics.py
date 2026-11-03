"""Real source builds preserve snapshot meaning across realistic generated pins."""

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import publication as p
import yaml
from publication import meaningful
from test_marketplace import ROOT, _root
from test_publication import Remote


def test_real_install_recipes_and_engine_inputs_distinguish_docs_from_policy(tmp_path):
  """Build actual install choices from real Git sources, including adapter changes."""
  source = tmp_path / "source"
  source.mkdir()
  _root(source)
  shutil.copytree(
    ROOT / "scripts", source / "scripts", ignore=shutil.ignore_patterns("__pycache__")
  )
  package = source / "skills/community/azure-networking"
  shutil.copytree(ROOT / "skills/community/azure-networking", package)

  def git(*args):
    """Use a real source repository without remote operations or signed commits."""
    return subprocess.check_output(["git", "-C", str(source), *args]).decode().strip()

  def build():
    """Execute the trusted builder CLI; package resources remain inert data."""
    subprocess.run(
      [
        sys.executable,
        str(source / "scripts/marketplace.py"),
        "--root",
        str(source),
        "generate",
      ],
      check=True,
      capture_output=True,
      text=True,
    )
    return json.loads((source / "catalog/catalog.json").read_bytes())

  git("init")
  git("config", "user.name", "Source fixture")
  git("config", "user.email", "fixture@example.com")
  git("config", "commit.gpgsign", "false")
  git("add", ".")
  git("commit", "-m", "source baseline")
  first = build()
  options = first["extensions"][0]["install-options"]
  assert options and options[0]["placements"]
  assert (
    f"/tree/{first['revision']}/skills/community/azure-networking"
    in options[0]["source-url"]
  )
  assert all(option["source"]["revision"] == first["revision"] for option in options)
  (source / "README.md").write_text("Docs-only source change\n", encoding="utf-8")
  git("add", "README.md")
  git("commit", "-m", "docs only")
  second = build()
  assert first["revision"] != second["revision"]
  assert first["engine"] == second["engine"]
  assert meaningful(first) == meaningful(second)

  config_path = source / "config/marketplace.yaml"
  config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
  config["publication"] = {"enabled": True}
  config["release-state"] = "development"
  config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
  git("add", "config/marketplace.yaml")
  git("commit", "-m", "operational switch only")
  assert meaningful(build()) == meaningful(second)

  config["community-intake"] = {
    "auto-publish": False,
    "max-new-packages-per-window": 10,
    "window-days": 7,
    "auto-publish-risk-ceiling": "elevated",
  }
  config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
  governed = build()
  for field, value in (
    ("max-new-packages-per-window", 9),
    ("window-days", 8),
    ("auto-publish-risk-ceiling", "low"),
  ):
    changed = json.loads(json.dumps(config))
    changed["community-intake"][field] = value
    config_path.write_text(yaml.safe_dump(changed), encoding="utf-8")
    assert meaningful(build()) != meaningful(governed)
  config["community-intake"]["auto-publish"] = True
  config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
  assert meaningful(build()) == meaningful(governed)

  # The builder is now executing this copied trusted adapter input, not a mocked hash.
  adapter = source / "scripts/install_choices.py"
  with adapter.open("a", encoding="utf-8") as stream:
    stream.write("\n# Changed trusted install adapter input.\n")
  changed_adapter = build()
  assert changed_adapter["engine"] != second["engine"]
  assert meaningful(changed_adapter) != meaningful(second)
  policy_path = source / "config/security-policy.yaml"
  policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
  policy["policy-version"] += 1
  policy_path.write_text(yaml.safe_dump(policy), encoding="utf-8")
  changed_policy = build()
  assert meaningful(changed_policy) != meaningful(changed_adapter)
  registry_path = source / "config/specialties.yaml"
  registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
  registry["specialties"][0]["owner-team"] = "@bcgov/new-security-owner"
  registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
  assert meaningful(build()) != meaningful(changed_policy)


def test_render_only_source_edit_changes_site_but_reuses_exact_accepted_catalogue(
  tmp_path,
):
  """Actual CLI/rendering edits stay separate from scan/authorization inputs."""
  source = tmp_path / "source"
  source.mkdir()
  _root(source)
  shutil.copytree(
    ROOT / "scripts", source / "scripts", ignore=shutil.ignore_patterns("__pycache__")
  )
  shutil.copytree(ROOT / "docs", source / "docs")
  shutil.copytree(
    ROOT / "skills/community/azure-networking",
    source / "skills/community/azure-networking",
  )
  alias = "bcgov-public/azure-networking"
  (source / "config/legacy-ids.json").write_text(
    json.dumps({alias: "bcgov-public/skill/azure-networking"}), encoding="utf-8"
  )

  def git(*args):
    """Run real source SCM; this fixture never touches a remote."""
    return subprocess.check_output(["git", "-C", str(source), *args]).decode().strip()

  def cli(script, *args):
    """Execute the public trusted command with copied actual sources."""
    subprocess.run(
      [sys.executable, str(source / "scripts" / script), "--root", str(source), *args],
      check=True,
      capture_output=True,
      text=True,
    )

  class RepositoryRemote(Remote):
    """Use real SCM ancestry behind the external publication fixture."""

    def is_descendant(self, older, newer):
      """Retain baseline ancestry and ask actual Git for subsequent sources."""
      return (
        older == "0" * 40
        or subprocess.run(
          ["git", "-C", str(source), "merge-base", "--is-ancestor", older, newer],
          check=False,
        ).returncode
        == 0
      )

  git("init")
  git("config", "user.name", "Source fixture")
  git("config", "user.email", "fixture@example.com")
  git("config", "commit.gpgsign", "false")
  git("add", ".")
  git("commit", "-m", "source baseline")
  cli("marketplace.py", "generate")
  first = json.loads((source / "catalog/catalog.json").read_bytes())
  before_cards = (source / "docs/_generated/catalog-cards.html").read_bytes()
  remote = RepositoryRemote()
  legacy = p.canonical(
    {
      "schema-version": "bcgov-marketplace-catalog/v1alpha1",
      "extensions": [{"id": alias}],
    }
  )
  remote.baseline.update({"ids": [alias], "digest": p.digest(legacy)})
  remote.items[0] = replace(remote.items[0], content=legacy)
  accepted = p.publish(
    remote,
    first,
    {"source": first["revision"], "run": "local"},
    baseline=remote.baseline,
    day="2026.11.03",
  )
  asset = tmp_path / "selected.json"
  asset.write_bytes(accepted.content)
  cli("build_site.py", "--catalog", str(asset), "--output", str(tmp_path / "before"))

  # Change only a user-facing card label, wherever the presentation module lives.
  presentation = next(
    path
    for path in (source / "scripts").glob("*.py")
    if "Source updated:" in path.read_text(encoding="utf-8")
  )
  presentation.write_text(
    presentation.read_text(encoding="utf-8").replace(
      "Source updated:", "Source last changed:"
    ),
    encoding="utf-8",
  )
  git("add", str(presentation.relative_to(source)))
  git("commit", "-m", "render-only label edit")
  cli("marketplace.py", "generate")
  second = json.loads((source / "catalog/catalog.json").read_bytes())
  assert (source / "docs/_generated/catalog-cards.html").read_bytes() != before_cards
  assert first["engine"] == second["engine"]
  assert first["authorization-inputs"] == second["authorization-inputs"]
  assert meaningful(first) == meaningful(second)
  replay = p.publish(
    remote,
    second,
    {"source": second["revision"], "run": "local"},
    baseline=remote.baseline,
    day="2026.11.03",
  )
  assert replay.action == "reuse"
  assert replay.content == accepted.content == remote.live
  cli("build_site.py", "--catalog", str(asset), "--output", str(tmp_path / "after"))
  assert (tmp_path / "after/assets/catalog.json").read_bytes() == accepted.content
  assert "Source updated:" in (tmp_path / "before/catalog.html").read_text(
    encoding="utf-8"
  )
  assert "Source last changed:" in (tmp_path / "after/catalog.html").read_text(
    encoding="utf-8"
  )
