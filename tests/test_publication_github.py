"""Real builder/coordinator/site behavior against an external GitHub API fixture."""

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import marketplace as m
import publication as p
from publish import ApiError, GitHubPublication

ROOT = Path(__file__).parents[1]


class GitHub:
  """Persist external release/tag/asset state without network or credentials."""

  def __init__(self):
    """Use actual legacy bytes, including the historical tag/source SHA split."""
    self.baseline = json.loads((ROOT / "config/publication-baseline.json").read_bytes())
    self.legacy = (ROOT / "tests/fixtures/publication/legacy-catalog.json").read_bytes()
    self.on = True
    self.items = [
      {
        "id": 1,
        "tag_name": self.baseline["tag"],
        "target_commitish": "main",
        "draft": False,
        "published_at": "2026-10-01T17:23:15Z",
      }
    ]
    self.assets = {1: self.legacy}
    self.refs = {self.baseline["tag"]: self.baseline["target"]}
    self.effects = []

  def listing(self, path):
    """Expose external lists after persistence."""
    if path.endswith("/releases"):
      return [dict(item) for item in self.items]
    if path.endswith("/tags"):
      return [{"name": name, "commit": {"sha": sha}} for name, sha in self.refs.items()]
    if path.endswith("/assets"):
      identifier = int(path.split("/")[-2])
      content = self.assets.get(identifier)
      return (
        []
        if content is None
        else [
          {
            "id": identifier,
            "name": "catalog.json",
            "state": "uploaded",
            "size": len(content),
            "digest": p.digest(content),
          }
        ]
      )
    raise AssertionError(path)

  def request(self, method, path, data=None, *, binary=False):
    """Implement the external API contract, including absent draft tag refs."""
    if method != "GET":
      self.effects.append((method, path, data))
    if "/git/ref/heads/main" in path:
      return {"object": {"sha": "f" * 40}}
    if "/contents/config/marketplace.yaml?ref=" in path:
      value = f"publication:\n  enabled: {str(self.on).lower()}\n".encode()
      return {"content": base64.b64encode(value).decode()}
    if "/git/ref/tags/" in path:
      tag = path.split("/tags/", 1)[1]
      if tag not in self.refs:
        raise ApiError("HTTP 404")
      return {"object": {"type": "commit", "sha": self.refs[tag]}}
    if binary:
      return self.assets[int(path.split("/")[-1])]
    if method == "POST" and path.endswith("/releases"):
      item = {**data, "id": len(self.items) + 1, "published_at": None}
      self.items.append(item)
      return item
    if path.startswith("https://uploads.github.com/"):
      identifier = int(path.split("/releases/", 1)[1].split("/")[0])
      assert identifier not in self.assets
      self.assets[identifier] = data
      return {"id": identifier}
    if "/releases/" in path:
      identifier = int(path.split("/")[-1])
      item = next(i for i in self.items if i["id"] == identifier)
      if method == "PATCH":
        item.update(data)
        item["published_at"] = "2026-11-03T12:34:56Z"
        self.refs[item["tag_name"]] = item["target_commitish"]
      return {
        **item,
        "upload_url": f"https://uploads.github.com/repos/bcgov/agent-marketplace/releases/{identifier}/assets{{?name,label}}",
      }
    raise AssertionError((method, path))


def test_actual_legacy_migration_exact_release_bytes_and_isolated_pages(tmp_path):
  """Legacy IDs survive; release, site metadata and staged Catalogue agree."""
  github = GitHub()
  adapter = GitHubPublication(ROOT, tmp_path, github)
  data, _ = m.build_catalog(ROOT)
  source = data["revision"]
  site = {"source": "b" * 40, "run": "fixture"}
  result = p.publish(
    adapter, data, site, baseline=github.baseline, day="2026.11.03", deploy=False
  )
  assert (
    (tmp_path / "docs/assets/catalog.json").read_bytes()
    == result.content
    == github.assets[2]
  )
  assert github.refs[result.release.tag] == source
  asset = json.loads(result.content)
  assert len(asset["publication"]["migration"]["aliases"]) == 9
  assert all(alias in asset["legacy-ids"] for alias in github.baseline["ids"])
  metadata = json.loads((tmp_path / "docs/assets/site-build.json").read_bytes())
  assert metadata["catalogue"]["release"]["published_at"] == "2026-11-03T12:34:56Z"
  assert metadata["catalogue"]["source"] == source
  assert metadata["site"]["source"] == "b" * 40
  assert metadata["catalogue"]["asset-digest"] == p.digest(result.content)
  assert "asset-digest" not in asset
  assert (tmp_path / "docs/catalog.html").exists()


def test_current_disabled_main_overrides_enabled_historical_checkout(tmp_path):
  """The real adapter reads main's present switch and cannot mutate when off."""
  github = GitHub()
  github.on = False
  adapter = GitHubPublication(ROOT, tmp_path, github)
  data, _ = m.build_catalog(ROOT)
  result = p.publish(
    adapter,
    data,
    {"source": "a" * 40, "run": "old"},
    baseline=github.baseline,
    day="2026.11.03",
    deploy=False,
  )
  assert result.action == "disabled"
  assert github.effects == []
