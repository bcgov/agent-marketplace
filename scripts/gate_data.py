"""Bounded immutable Git data supplied to the existing trusted package analyzer."""

from __future__ import annotations

import base64
import hashlib
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath

import marketplace as m


class Incomplete(Exception):
  """Missing authoritative facts require review, never inferred eligibility."""


def safe_path(path: str) -> bool:
  """Keep Git names inert and inside an isolated, portable data directory."""
  return (
    isinstance(path, str)
    and bool(path)
    and not any(ord(char) < 32 or char in "\\:" for char in path)
    and not path.startswith("/")
    and all(
      part not in {"", ".", ".."} and not part.endswith((".", " "))
      for part in path.split("/")
    )
  )


def package_path(path: str) -> str | None:
  """Identify package roots from any resource or native-content path."""
  parts = path.split("/")
  if len(parts) >= 4 and parts[0] in m.TYPE_DIRECTORIES:
    return "/".join(parts[:3])
  return None


class RepositoryData:
  """Read complete trees and verify bounded immutable blobs without a PR checkout."""

  def __init__(self, request):
    """Accept the external GitHub request boundary, caching only immutable data."""
    self.request = request
    self.trees = {}
    self.blobs = {}

  def tree(self, revision: str) -> dict:
    """Reject truncated, ambiguous or malformed recursive inventories."""
    if revision in self.trees:
      return self.trees[revision]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
      raise Incomplete("A complete immutable source revision is missing.")
    response = self.request("GET", f"git/trees/{revision}?recursive=1")
    entries = response.get("tree")
    if (
      response.get("truncated") is not False
      or not isinstance(entries, list)
      or len(entries) >= 100000
    ):
      raise Incomplete(
        "Package inventory is truncated or unavailable; "
        "retry with complete tree evidence."
      )
    tree = {}
    folded = set()
    for entry in entries:
      path = entry.get("path")
      if not safe_path(path) or path in tree or path.casefold() in folded:
        raise Incomplete("Tree paths are ambiguous or cannot be safely inventoried.")
      if not re.fullmatch(r"[0-9a-f]{40}", entry.get("sha", "")):
        raise Incomplete("Tree entry lacks an immutable object identity.")
      tree[path] = entry
      folded.add(path.casefold())
    self.trees[revision] = tree
    return tree

  def blob(self, entry: dict, limit: int = m.MAX_FILE_BYTES) -> bytes:
    """Verify Git's blob hash and declared length before parsing any bytes."""
    if entry.get("type") != "blob" or entry.get("mode") != "100644":
      raise m.MarketplaceError("Package files must be regular, non-executable blobs.")
    size = entry.get("size")
    if not isinstance(size, int) or size < 0 or size > limit:
      raise m.MarketplaceError("A package file exceeds the supported size limit.")
    sha = entry["sha"]
    if sha not in self.blobs:
      response = self.request("GET", f"git/blobs/{sha}")
      if response.get("encoding") != "base64" or response.get("size") != size:
        raise Incomplete("Blob content or length is unavailable.")
      encoded = response.get("content", "")
      if not isinstance(encoded, str) or len(encoded) > (limit * 2):
        raise Incomplete("Blob response exceeds the bounded content envelope.")
      try:
        content = base64.b64decode("".join(encoded.split()), validate=True)
      except (ValueError, TypeError) as exc:
        raise Incomplete("Blob encoding is invalid.") from exc
      actual = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
      if len(content) != size or actual != sha:
        raise Incomplete("Blob bytes do not match their immutable object identity.")
      self.blobs[sha] = content
    return self.blobs[sha]

  def records(self, revision: str, *, include_drafts: bool = False) -> dict:
    """Inventory canonical identities, including unchanged retired reservations."""
    records = {}
    for path, entry in self.tree(revision).items():
      parts = path.split("/")
      if (
        len(parts) != 4
        or parts[0] not in m.TYPE_DIRECTORIES
        or parts[-1] != m.MANIFEST_NAME
      ):
        continue
      if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", parts[2]):
        raise m.MarketplaceError("Use canonical kebab-case Extension names.")
      try:
        manifest = m.load_yaml_text(
          self.blob(entry).decode("utf-8"), Path(m.MANIFEST_NAME)
        )
      except UnicodeError as exc:
        raise m.MarketplaceError("Manifests must be UTF-8 text.") from exc
      if manifest.get("lifecycle") == "draft" and not include_drafts:
        continue
      identity = f"bcgov-public/{m.TYPE_DIRECTORIES[parts[0]]}/{parts[2]}"
      if identity in records:
        raise m.MarketplaceError(
          "Canonical identities must be unique across Specialties."
        )
      records[identity] = {
        **manifest,
        "id": identity,
        "path": "/".join(parts[:3]),
        "specialty": parts[1],
        "lifecycle": manifest.get("lifecycle", "active"),
        "source": {"path": "/".join(parts[:3])},
      }
    return records

  def analyze(
    self, trusted_root: Path, base: str, head: str, changed: set[str]
  ) -> dict:
    """Analyze every retained affected-package byte with trusted code and policy."""
    previous, proposed = self.records(base), self.records(head, include_drafts=True)
    affected = {package_path(path) for path in changed} - {None}
    tree = self.tree(head)
    analyses = {}
    hard = []
    for path, entry in tree.items():
      if path.split("/")[0] not in m.TYPE_DIRECTORIES:
        continue
      if entry.get("type") == "tree" and entry.get("mode") == "040000":
        continue
      if (
        entry.get("type") != "blob"
        or entry.get("mode") != "100644"
        or len(path.split("/")) < 4
      ):
        hard.append(
          "Extension paths must contain regular, non-executable files "
          "in canonical package directories."
        )
    with tempfile.TemporaryDirectory(prefix="merge-gate-data-") as directory:
      root = Path(directory)
      for name in ("config", "schemas"):
        shutil.copytree(trusted_root / name, root / name)
      # Fetch controls/policy from the immutable trusted base.
      for path, entry in self.tree(base).items():
        if path.startswith(("config/", "schemas/")) and entry["type"] != "tree":
          target = root.joinpath(*PurePosixPath(path).parts)
          target.parent.mkdir(parents=True, exist_ok=True)
          target.write_bytes(self.blob(entry))
      config = m.load_marketplace_config(root)
      policy = m.load_security_policy(root)
      engine = m.engine_identity(root)
      for package in sorted(affected):
        entries = [
          (path, entry)
          for path, entry in tree.items()
          if path.startswith(package + "/") and entry["type"] != "tree"
        ]
        if not entries:
          continue  # Reservation validation below rejects deletion of an identity.
        if (
          len(entries) > m.MAX_FILES
          or sum(entry.get("size", 0) for _, entry in entries) > m.MAX_PACKAGE_BYTES
        ):
          hard.append("An affected Extension exceeds package inventory limits.")
          continue
        try:
          for path, entry in entries:
            target = root.joinpath(*PurePosixPath(path).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.blob(entry))
          analysis = m.analyze_submission(root, root / package)
          if not analysis["inventory-complete"] or len(analysis["files"]) != len(
            entries
          ):
            raise Incomplete("Analyzed package inventory is incomplete.")
          manifest, errors = m.validate_manifest(
            root / package / m.MANIFEST_NAME, m.load_schema(root)
          )
          if errors or manifest is None:
            raise m.MarketplaceError(
              "Correct the affected Extension Manifest/native format."
            )
          identity = manifest["id"]
          analyses[identity] = analysis
          proposed[identity].update(manifest)
          if analysis["scan"]["outcome"] != "passed":
            hard.extend(
              sorted(
                {
                  finding["rule-id"] + ": " + finding["remediation"]
                  for finding in m.public_scan(analysis["scan"])["findings"]
                  if finding["disposition"] == "blocking"
                }
              )
            )
        except m.MarketplaceError:
          hard.append(
            "Correct the affected Extension's Manifest, native format, "
            "paths, modes or resource declarations."
          )
    # The same transition policy is used by unprivileged validation and this adapter.
    try:
      transitions = m.transition_facts(previous, proposed, changed)
    except m.MarketplaceError:
      hard.append(
        "Retain a non-active Manifest for every retired trusted-base identity; "
        "every changed package needs a Manifest."
      )
      transitions = []
    for identity, record in proposed.items():
      seen = {identity}
      while target := record.get("moved-to"):
        if target not in proposed or target in seen:
          hard.append(
            "Replacement targets must exist and replacement chains must be acyclic."
          )
          break
        seen.add(target)
        record = proposed[target]
    return {
      "packages": [
        {**fact, "risk": analyses.get(fact["id"], {}).get("risk", "high")}
        for fact in transitions
      ],
      "analyses": analyses,
      "hard-errors": hard,
      "engine": engine,
      "config": config,
      "policy": policy,
    }
