"""Deterministic snapshot binding and guarded immutable publication coordination."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class PublicationError(RuntimeError):
  """Publication state could not be proved safe to advance."""


def git(root: Path, *args: str) -> str:
  """Read source history without executing contributed package files."""
  result = subprocess.run(
    ["git", "-C", str(root), *args], capture_output=True, check=False
  )
  if result.returncode:
    raise PublicationError(
      "Git history unavailable: " + result.stderr.decode(errors="replace")
    )
  return result.stdout.decode("utf-8")


def source_dates(root: Path, history_start: str, head: str = "HEAD") -> dict:
  """Derive source dates strictly after a reachable first-parent baseline."""
  chain = git(root, "rev-list", "--first-parent", "--reverse", head).splitlines()
  if history_start not in chain:
    raise PublicationError("history-start must be a reachable first-parent full SHA")
  types = {
    "skills": "skill",
    "prompts": "prompt",
    "instructions": "instructions",
    "agents": "agent",
  }
  dates = {}
  previous = {}
  for index, revision in enumerate(chain[chain.index(history_start) :]):
    entries = git(root, "ls-tree", "-r", "-z", revision, "--", *types).split("\0")
    packages = {}
    for entry in filter(None, entries):
      info, path = entry.split("\t", 1)
      parts = path.split("/")
      if len(parts) >= 4 and parts[0] in types:
        identity = f"bcgov-public/{types[parts[0]]}/{parts[2]}"
        packages.setdefault(identity, {})[path] = info
    # Only a Manifest declares an Extension; loose content is validated separately.
    packages = {
      identity: files
      for identity, files in packages.items()
      if any(path.endswith("/bcgov-extension.yaml") for path in files)
    }
    timestamp = datetime.fromtimestamp(
      int(git(root, "show", "-s", "--format=%ct", revision).strip()), UTC
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    for identity, files in packages.items():
      if identity not in dates:
        dates[identity] = {"added": timestamp if index else None, "updated": None}
      if index and previous.get(identity) != files:
        dates[identity]["updated"] = timestamp
    previous = packages
  return {identity: dates[identity] for identity in previous}


def canonical(data: dict) -> bytes:
  """Serialize immutable Catalogue bytes without wall-clock metadata."""
  return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()


def digest(data: bytes) -> str:
  """Return an externally recorded asset digest, never embedded in itself."""
  return "sha256:" + hashlib.sha256(data).hexdigest()


def meaningful(catalog: dict) -> dict:
  """Normalize only generated snapshot slots, retaining real install/policy data."""
  result = copy.deepcopy(catalog)
  for key in ("revision", "version", "publication", "release-state"):
    result.pop(key, None)
  for record in result.get("extensions", []):
    source = record.get("source", {})
    sha = source.pop("revision", None)
    for choice in record.get("install-options", []):
      coordinate = choice.get("source", {})
      if coordinate.get("revision") == sha:
        coordinate.pop("revision")
      expected = f"{source.get('repository')}/tree/{sha}/{source.get('path')}"
      if choice.get("source-url") == expected:
        choice["source-url"] = "snapshot-source"
  return result


@dataclass(frozen=True)
class Release:
  """Observed release state; sha is the independently resolved tag target."""

  tag: str
  sha: str
  content: bytes | None
  draft: bool
  published_at: str | None
  id: int | None = None


@dataclass(frozen=True)
class Result:
  """Snapshot bytes and site coordinates, separate from actual event evidence."""

  action: str
  content: bytes
  site: dict
  release: Release | None = None
  deployment: dict | None = None


def newest(adapter, baseline: dict) -> Release:
  """Validate an unbroken accepted lineage rooted in the explicit legacy asset."""
  releases = [r for r in adapter.releases() if not r.draft]
  roots = [r for r in releases if r.tag == baseline["tag"]]
  if len(roots) != 1:
    raise PublicationError("Missing explicit legacy baseline; history is not a reset")
  current = roots[0]
  if (
    current.sha != baseline["target"]
    or current.content is None
    or digest(current.content) != baseline["digest"]
    or not current.published_at
  ):
    raise PublicationError("Legacy baseline target/bytes/publication mismatch")
  data = json.loads(current.content)
  if data.get("schema-version") != "bcgov-marketplace-catalog/v1alpha1" or sorted(
    r["id"] for r in data["extensions"]
  ) != sorted(baseline["ids"]):
    raise PublicationError("Legacy baseline schema/identities mismatch")
  if baseline.get("source") is not None and data.get("revision") != baseline["source"]:
    raise PublicationError("Legacy baseline source mismatch")
  remaining = [r for r in releases if r != current]
  while remaining:
    children = []
    for release in remaining:
      if release.content is None or not release.published_at:
        raise PublicationError("Published Catalogue lacks asset/event evidence")
      data = json.loads(release.content)
      if (
        data.get("schema-version") != "bcgov-marketplace/v1"
        or data.get("revision") != release.sha
        or data.get("version") != release.tag
        or not re.fullmatch(r"[0-9a-f]{40}", release.sha)
      ):
        raise PublicationError("Published Catalogue source/tag/schema mismatch")
      if data.get("publication", {}).get("parent") == {
        "tag": current.tag,
        "digest": digest(current.content),
      }:
        children.append(release)
    if len(children) != 1:
      raise PublicationError("Publication lineage is missing or forked")
    child = children[0]
    if not adapter.is_descendant(current.sha, child.sha):
      raise PublicationError("Accepted publication source ancestry moved backward")
    if current.tag == baseline["tag"]:
      transition = json.loads(child.content)
      aliases = transition.get("legacy-ids", {})
      migration = transition.get("publication", {}).get("migration", {})
      identities = {r["id"] for r in transition.get("extensions", [])}
      if (
        migration.get("tag") != current.tag
        or migration.get("digest") != digest(current.content)
        or migration.get("aliases") != aliases
        or not set(baseline["ids"]).issubset(aliases)
        or not set(aliases.values()).issubset(identities)
      ):
        raise PublicationError("Accepted first-v1 migration evidence is invalid")
    current = child
    remaining.remove(current)
  return current


def bind(candidate: dict, tag: str, parent: Release, baseline: dict) -> bytes:
  """Bind generated coordinates once, recording the exact accepted predecessor."""
  data = copy.deepcopy(candidate)
  data["version"] = tag
  data["release-state"] = "published"
  data["publication"] = {
    "parent": {"tag": parent.tag, "digest": digest(parent.content)}
  }
  if parent.tag == baseline["tag"]:
    aliases = data.get("legacy-ids", {})
    if not set(baseline["ids"]).issubset(aliases):
      raise PublicationError("First-v1 migration must preserve every legacy identity")
    data["publication"]["migration"] = {
      "tag": parent.tag,
      "digest": digest(parent.content),
      "aliases": aliases,
    }
  return canonical(data)


def guard_deploy(adapter, selected: Release, baseline: dict) -> bool:
  """Refuse stale replay and honor current-main disable immediately before deploy."""
  if not adapter.enabled():
    return False
  latest = newest(adapter, baseline)
  if latest.tag != selected.tag or latest.content != selected.content:
    raise PublicationError("Superseded Catalogue cannot be deployed as current")
  return adapter.enabled()


def change_notes(previous: dict, candidate: dict) -> str:
  """Identify package/lifecycle changes and meaningful evidence/config changes."""
  old = {r["id"]: r for r in previous.get("extensions", [])}
  new = {r["id"]: r for r in candidate.get("extensions", [])}
  changes = [
    f"- {identity}: {new[identity].get('lifecycle', 'active')}"
    for identity in sorted(new)
    if old.get(identity) != new[identity]
  ]
  changed_inputs = sorted(
    key
    for key in set(previous) | set(candidate)
    if key != "extensions" and previous.get(key) != candidate.get(key)
  )
  if changed_inputs:
    changes.append("Catalogue inputs changed: " + ", ".join(changed_inputs))
  return (
    "Immutable Catalogue snapshot.\n\n"
    + "\n".join(changes)
    + (
      "\n\nIncludes effective metadata, install support, policy/engine findings, "
      "and Specialty ownership/flair changes where applicable."
    )
  )


def publish(
  adapter,
  candidate: dict,
  site: dict,
  *,
  baseline: dict,
  day: str,
  deploy: bool = True,
  recover: bool = False,
) -> Result:
  """Build first, resume matching drafts, publish once, and deploy exact bytes."""
  if not re.fullmatch(r"[0-9a-f]{40}", candidate.get("revision", "")):
    raise PublicationError("Snapshot source must be a full SHA")
  if not adapter.enabled():
    adapter.prepare_site(canonical(candidate), site)
    return Result("disabled", canonical(candidate), site)
  previous = newest(adapter, baseline)
  if not recover and not adapter.is_descendant(previous.sha, candidate["revision"]):
    raise PublicationError("Stale source cannot supersede a newer accepted Catalogue")
  previous_data = json.loads(previous.content)
  unchanged = meaningful(candidate) == meaningful(previous_data)
  if recover or unchanged:
    if previous_data.get("schema-version") != "bcgov-marketplace/v1":
      raise PublicationError("Newest recovery requires an accepted v1 snapshot")
    selected = previous
    action = "reuse"
  else:
    drafts = [r for r in adapter.releases() if r.draft]
    matching = [r for r in drafts if r.sha == candidate["revision"]]
    if drafts and not matching:
      raise PublicationError("Incomplete draft source SHA differs; refusing duplicate")
    if len(matching) > 1:
      raise PublicationError("Ambiguous incomplete drafts")
    if matching:
      selected = matching[0]
      content = bind(candidate, selected.tag, previous, baseline)
      if selected.content is not None and selected.content != content:
        raise PublicationError("Draft asset collision: differing immutable bytes")
    else:
      tags = adapter.tags()
      releases = {r.tag for r in adapter.releases()}
      occupied = set(tags) | releases
      orphans = [
        tag
        for tag, sha in tags.items()
        if tag not in releases
        and sha == candidate["revision"]
        and re.fullmatch(r"catalog-\d{4}\.\d{2}\.\d{2}(?:\.\d+)?", tag)
      ]
      if len(orphans) > 1:
        raise PublicationError("Ambiguous incomplete Catalogue tags")
      tag = orphans[0] if orphans else f"catalog-{day}"
      suffix = 2
      while not orphans and tag in occupied:
        tag = f"catalog-{day}.{suffix}"
        suffix += 1
      content = bind(candidate, tag, previous, baseline)
      selected = Release(tag, candidate["revision"], None, True, None)
    adapter.prepare_site(content, site)
    if not adapter.enabled():
      return Result("disabled", content, site)
    if newest(adapter, baseline) != previous:
      raise PublicationError("Publication predecessor changed; reconcile latest main")
    tags = adapter.tags()
    if selected.tag in tags and tags[selected.tag] != selected.sha:
      raise PublicationError("Tag target collision")
    if not matching:
      if not adapter.enabled():
        return Result("disabled", content, site)
      selected = adapter.create(
        selected.tag,
        selected.sha,
        change_notes(meaningful(previous_data), meaningful(candidate)),
      )
    if selected.content is None:
      if not adapter.enabled():
        return Result("disabled", content, site)
      adapter.upload(selected, content)
      selected = next(r for r in adapter.releases() if r.tag == selected.tag)
    if selected.content != content:
      raise PublicationError("Uploaded bytes differ; refusing publication")
    if not adapter.enabled():
      return Result("disabled", content, site)
    adapter.publish(selected)
    selected = newest(adapter, baseline)
    if selected.content != content:
      raise PublicationError("Published asset changed")
    action = "publish"
  adapter.prepare_site(selected.content, site)
  deployment = None
  if not guard_deploy(adapter, selected, baseline):
    return Result("disabled", selected.content, site, selected)
  if deploy:
    deployment = adapter.deploy(selected.content, site)
  return Result(action, selected.content, site, selected, deployment)
