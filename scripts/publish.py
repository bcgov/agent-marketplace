"""GitHub release adapter and workflow entrypoint; never writes source refs or main."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import marketplace
from build_site import build_site
from publication import (
  PublicationError,
  Release,
  canonical,
  digest,
  git,
  guard_deploy,
  publish,
)

REPOSITORY = "bcgov/agent-marketplace"


class ApiError(PublicationError):
  """An API request failed without authorizing a history reset or overwrite."""


class GitHubApi:
  """Small transport boundary using the runner's existing GitHub job token."""

  def request(self, method: str, path: str, data=None, *, binary=False):
    """Send one bounded API operation without shell expansion or token output."""
    command = [
      "gh",
      "api",
      path,
      "--method",
      method,
      "--header",
      "X-GitHub-Api-Version: 2026-03-10",
      "--header",
      "Accept: "
      + ("application/octet-stream" if binary else "application/vnd.github+json"),
    ]
    with tempfile.TemporaryDirectory(prefix="catalog-api-") as directory:
      if data is not None:
        payload = Path(directory) / "payload"
        payload.write_bytes(data if isinstance(data, bytes) else canonical(data))
        command += [
          "--input",
          str(payload),
          "--header",
          "Content-Type: application/json",
        ]
      result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
      raise ApiError(result.stderr.decode(errors="replace"))
    return result.stdout if binary else json.loads(result.stdout)

  def listing(self, path: str) -> list:
    """Read every page; an API failure is never an empty successful history."""
    values = []
    for page in range(1, 1001):
      batch = self.request("GET", f"{path}?per_page=100&page={page}")
      if not isinstance(batch, list):
        raise ApiError("Unexpected paginated API response")
      values.extend(batch)
      if len(batch) < 100:
        return values
    raise ApiError("Publication history exceeds bounded pagination")


class GitHubPublication:
  """Reconcile immutable releases before guarded Pages workflow steps."""

  def __init__(self, root: Path, output: Path, api=None):
    """Keep trusted source, isolated site output and API authority explicit."""
    self.root = root
    self.output = output
    self.api = api or GitHubApi()
    self.prefix = f"repos/{REPOSITORY}"
    self.observed = []

  def enabled(self) -> bool:
    """Fetch the switch from current trusted main, never from historical config."""
    ref = self.api.request("GET", f"{self.prefix}/git/ref/heads/main")
    sha = ref["object"]["sha"]
    blob = self.api.request(
      "GET", f"{self.prefix}/contents/config/marketplace.yaml?ref={sha}"
    )
    config = marketplace.load_yaml_text(
      base64.b64decode(blob["content"]).decode("utf-8"),
      Path("current-main/config/marketplace.yaml"),
    )
    control = config.get("publication", {"enabled": False})
    if (
      not isinstance(control, dict)
      or set(control) != {"enabled"}
      or type(control["enabled"]) is not bool
    ):
      raise PublicationError("Current-main publication control is invalid")
    return control["enabled"]

  def require_enabled(self) -> None:
    """Recheck immediately inside every release mutation adapter."""
    if not self.enabled():
      raise PublicationError(
        "Current trusted main disabled publication; no effect performed"
      )

  def is_descendant(self, older: str, newer: str) -> bool:
    """Prove selected source ancestry using the workflow's full main history."""
    result = subprocess.run(
      ["git", "-C", str(self.root), "merge-base", "--is-ancestor", older, newer],
      capture_output=True,
      check=False,
    )
    if result.returncode not in {0, 1}:
      raise PublicationError("Cannot prove snapshot source ancestry")
    return result.returncode == 0

  def tag_target(self, tag: str) -> str | None:
    """Resolve lightweight or annotated remote refs independently of a release."""
    try:
      value = self.api.request(
        "GET", f"{self.prefix}/git/ref/tags/{quote(tag, safe='')}"
      )["object"]
    except ApiError as exc:
      if "HTTP 404" in str(exc):
        return None
      raise
    for _ in range(10):
      if value["type"] == "commit":
        return value["sha"]
      if value["type"] != "tag":
        break
      value = self.api.request("GET", f"{self.prefix}/git/tags/{value['sha']}")[
        "object"
      ]
    raise PublicationError("Catalogue tag does not resolve to a commit")

  def tags(self) -> dict:
    """Inventory all occupied remote tags, including tags without releases."""
    return {
      item["name"]: item["commit"]["sha"]
      for item in self.api.listing(f"{self.prefix}/tags")
    }

  def releases(self) -> list[Release]:
    """Download and verify Catalogue assets from every published release and draft."""
    observed = []
    for item in self.api.listing(f"{self.prefix}/releases"):
      tag = item["tag_name"]
      if not tag.startswith("catalog-"):
        continue
      assets = self.api.listing(f"{self.prefix}/releases/{item['id']}/assets")
      catalogs = [a for a in assets if a["name"] == "catalog.json"]
      legacy = tag == "catalog-2026.10.01"
      if len(catalogs) > 1 or (
        not legacy and any(a["name"] != "catalog.json" for a in assets)
      ):
        raise PublicationError("Catalogue release has an unexpected asset set")
      content = None
      if catalogs:
        asset = catalogs[0]
        if asset.get("state") != "uploaded" or not asset.get("size"):
          raise PublicationError(
            "Incomplete starter asset; operator diagnosis required, never overwritten"
          )
        content = self.api.request(
          "GET", f"{self.prefix}/releases/assets/{asset['id']}", binary=True
        )
        if len(content) != asset["size"] or asset.get("digest") != digest(content):
          raise PublicationError("Remote asset size/digest mismatch")
      sha = self.tag_target(tag)
      if sha is None:
        if not item["draft"]:
          raise PublicationError("Published release has no actual tag")
        sha = item["target_commitish"]
      observed.append(
        Release(tag, sha, content, item["draft"], item["published_at"], item["id"])
      )
    self.observed = observed
    return observed

  def prepare_site(self, content: bytes, site: dict) -> None:
    """Build before effects and copy the asset without reserializing."""
    release = next(
      (r for r in self.observed if r.content == content and not r.draft), None
    )
    evidence = (
      {
        "id": release.id,
        "published_at": release.published_at,
        "url": f"https://github.com/{REPOSITORY}/releases/tag/{release.tag}",
      }
      if release
      else None
    )
    build_site(self.root, self.output / "docs", content, site, evidence)

  def create(self, tag: str, sha: str, notes: str) -> Release:
    """Create a draft at the selected full SHA; GitHub creates its tag on publish."""
    self.require_enabled()
    target = self.tag_target(tag)
    if target is not None and target != sha:
      raise PublicationError("Tag target collision before draft creation")
    self.require_enabled()
    item = self.api.request(
      "POST",
      f"{self.prefix}/releases",
      {
        "tag_name": tag,
        "target_commitish": sha,
        "name": tag,
        "body": notes,
        "draft": True,
        "prerelease": False,
      },
    )
    return Release(tag, sha, None, True, None, item["id"])

  def upload(self, release: Release, content: bytes) -> None:
    """Upload one catalog.json without delete/clobber or overwrite operations."""
    item = self.api.request("GET", f"{self.prefix}/releases/{release.id}")
    if not item["draft"]:
      raise PublicationError("Cannot upload to a published release")
    url = item["upload_url"].split("{", 1)[0] + "?name=catalog.json"
    if not url.startswith(f"https://uploads.github.com/repos/{REPOSITORY}/"):
      raise PublicationError("Unexpected release upload endpoint")
    self.require_enabled()
    self.api.request("POST", url, content)

  def publish(self, release: Release) -> None:
    """Publish only an uploaded draft with its expected actual tag target."""
    target = self.tag_target(release.tag)
    if target is not None and target != release.sha:
      raise PublicationError("Tag target changed before publication")
    self.require_enabled()
    self.api.request("PATCH", f"{self.prefix}/releases/{release.id}", {"draft": False})


def main() -> None:
  """Plan from latest-main checkout, or guard the exact selected Pages artifact."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--output", type=Path, required=True)
  parser.add_argument(
    "--mode", choices=["reconcile", "newest", "check-live"], default="reconcile"
  )
  args = parser.parse_args()
  root = Path(__file__).resolve().parents[1]
  config = marketplace.load_marketplace_config(root)
  baseline = json.loads((root / "config/publication-baseline.json").read_text())
  adapter = GitHubPublication(root, args.output.resolve())
  if args.mode == "check-live":
    selection = json.loads((args.output / "selection.json").read_bytes())
    selected = Release(
      selection["tag"],
      selection["sha"],
      (args.output / "docs/assets/catalog.json").read_bytes(),
      False,
      None,
    )
    allowed = guard_deploy(adapter, selected, baseline)
    result = {"allowed": str(allowed).lower()}
  else:
    if not config.get("history-start"):
      raise PublicationError("Publication requires an explicit reachable history-start")
    marketplace.validate(root)
    data, _ = marketplace.build_catalog(root)
    site = {
      "source": git(root, "rev-parse", "HEAD").strip(),
      "run": os.environ.get("GITHUB_RUN_ID", "local"),
      "attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
    }
    outcome = publish(
      adapter,
      data,
      site,
      baseline=baseline,
      day=datetime.now(UTC).strftime("%Y.%m.%d"),
      deploy=False,
      recover=args.mode == "newest",
    )
    result = {
      "allowed": str(outcome.action != "disabled").lower(),
      "action": outcome.action,
    }
    if outcome.release:
      (args.output / "selection.json").write_bytes(
        canonical(
          {
            "tag": outcome.release.tag,
            "sha": outcome.release.sha,
            "digest": digest(outcome.content),
            "release-id": outcome.release.id,
            "published_at": outcome.release.published_at,
          }
        )
      )
  print(json.dumps(result))
  if os.environ.get("GITHUB_OUTPUT"):
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
      for key, value in result.items():
        stream.write(f"{key}={value}\n")


if __name__ == "__main__":
  main()
