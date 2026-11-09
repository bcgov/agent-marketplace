"""Authenticate grouped Dependabot metadata and restrict dependency-only diffs."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from urllib.parse import urlparse

import marketplace as m
import yaml

BOT_ID = 49699333


class WorkflowLoader(m.StrictSafeLoader):
  """Use strict mapping/alias handling with GitHub's YAML 1.2 boolean spelling."""


WorkflowLoader.yaml_implicit_resolvers = {
  key: [
    (tag, expression) for tag, expression in values if tag != "tag:yaml.org,2002:bool"
  ]
  for key, values in m.StrictSafeLoader.yaml_implicit_resolvers.items()
}
WorkflowLoader.add_implicit_resolver(
  "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.I), list("tTfF")
)


def workflow(content: bytes) -> dict:
  """Read a bounded workflow as inert data with unique string keys and no aliases."""
  value = yaml.load(content.decode("utf-8"), Loader=WorkflowLoader)
  if not isinstance(value, dict):
    raise ValueError("Workflow must be a mapping")
  return value


def dependency_workflow(before: bytes, after: bytes, names: set[str]) -> bool:
  """Allow only action ref changes with identical owner/path and all other fields."""
  try:
    old, new = workflow(before), workflow(after)
    changed = False
    for job_name, old_job in old.get("jobs", {}).items():
      new_job = new["jobs"][job_name]
      for index, old_step in enumerate(old_job.get("steps", [])):
        new_step = new_job["steps"][index]
        original, proposed = old_step.get("uses"), new_step.get("uses")
        if original == proposed:
          continue
        if not isinstance(original, str) or not isinstance(proposed, str):
          return False
        old_action, old_ref = original.rsplit("@", 1)
        new_action, new_ref = proposed.rsplit("@", 1)
        if (
          old_action != new_action
          or old_action not in names
          or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+", old_action)
          or not re.fullmatch(r"[A-Za-z0-9_.+/-]+", new_ref)
          or not old_ref
          or not new_ref
        ):
          return False
        new_step["uses"] = original
        changed = True
    return changed and old == new
  except (yaml.YAMLError, UnicodeError, KeyError, TypeError, ValueError, IndexError):
    return False


def dependency_manifest(before: bytes, after: bytes, names: set[str]) -> bool:
  """Allow constraint updates only in existing project/dependency-group entries."""
  old, new = tomllib.loads(before.decode()), tomllib.loads(after.decode())
  changed = False
  containers = [(old.get("project", {}), new.get("project", {}), "dependencies")]
  for group in old.get("dependency-groups", {}):
    containers.append((old["dependency-groups"], new["dependency-groups"], group))
  for left, right, field in containers:
    original, proposed = left.get(field, []), right.get(field, [])
    if len(original) != len(proposed):
      return False
    for index, (a, b) in enumerate(zip(original, proposed, strict=True)):
      if a == b:
        continue
      if not isinstance(a, str) or not isinstance(b, str):
        return False
      match_a = re.fullmatch(r"([A-Za-z0-9_.-]+)([<>=!~0-9.* ,]+)", a)
      match_b = re.fullmatch(r"([A-Za-z0-9_.-]+)([<>=!~0-9.* ,]+)", b)
      if (
        not match_a
        or not match_b
        or match_a[1] != match_b[1]
        or match_a[1] not in names
      ):
        return False
      right[field][index] = a
      changed = True
  return changed and old == new


def dependency_lock(before: bytes, after: bytes) -> bool:
  """Accept uv dependency data while rejecting new executable/local/VCS sources."""
  old, new = tomllib.loads(before.decode()), tomllib.loads(after.decode())
  old_packages, packages = old.pop("package"), new.pop("package")
  if old != new or not isinstance(packages, list):
    return False
  roots = [item for item in old_packages if "virtual" in item.get("source", {})]
  new_roots = []
  for package in packages:
    source = package.get("source", {})
    if "virtual" in source:
      new_roots.append(package)
      continue
    if source != {"registry": "https://pypi.org/simple"}:
      return False
    if set(package) - {
      "name",
      "version",
      "source",
      "dependencies",
      "optional-dependencies",
      "sdist",
      "wheels",
      "resolution-markers",
    }:
      return False
    for artifact in [package.get("sdist"), *package.get("wheels", [])]:
      if artifact is None:
        continue
      url = urlparse(artifact.get("url", ""))
      if (
        url.scheme != "https"
        or url.netloc != "files.pythonhosted.org"
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("hash", ""))
      ):
        return False
  # Virtual-project dependency metadata may change; its identity/source may not.
  for items in (roots, new_roots):
    for item in items:
      for field in (
        "dependencies",
        "dev-dependencies",
        "optional-dependencies",
        "metadata",
      ):
        item.pop(field, None)
  return roots == new_roots


def authorize(
  pr: dict, commit: dict, data, base: str, head: str, changed: set[str]
) -> bool:
  """Require authentic exact-head bot identity, signed group and trusted config."""
  try:
    for actor in (pr["user"], commit["author"]):
      if (
        actor.get("id") != BOT_ID
        or actor.get("login") != "dependabot[bot]"
        or actor.get("type") != "Bot"
      ):
        return False
    if commit["sha"] != head or not commit["commit"]["verification"]["verified"]:
      return False
    if pr["head"]["repo"]["id"] != pr["base"]["repo"]["id"]:
      return False
    message = commit["commit"]["message"]
    if len(message) > 65536:
      return False
    fragment = re.search(r"^---\n(.*?)\n\.\.\.\s*$", message, re.M | re.S)
    groups = re.findall(r"^dependency-group: ([A-Za-z0-9_-]+)\s*$", message, re.M)
    if not fragment or len(groups) != 1:
      return False
    metadata = m.load_yaml_text(fragment[1], Path("dependabot-metadata"))
    dependencies = metadata.get("updated-dependencies")
    if not isinstance(dependencies, list) or not 1 <= len(dependencies) <= 100:
      return False
    names = {item["dependency-name"] for item in dependencies}
    if not all(isinstance(name, str) and 0 < len(name) < 256 for name in names):
      return False
    parts = pr["head"]["ref"].split("/")
    if (
      len(parts) != 3 or parts[0] != "dependabot" or not parts[2].startswith(groups[0])
    ):
      return False
    ecosystem = {
      "github_actions": "github-actions",
      "github-actions": "github-actions",
      "uv": "uv",
    }.get(parts[1])
    old_tree, new_tree = data.tree(base), data.tree(head)
    config = m.load_yaml_text(
      data.blob(old_tree[".github/dependabot.yml"]).decode(), Path("dependabot.yml")
    )
    configs = [
      item
      for item in config["updates"]
      if item["package-ecosystem"] == ecosystem
      and item.get("directory") == "/"
      and groups[0] in item.get("groups", {})
    ]
    if len(configs) != 1 or configs[0]["groups"][groups[0]].get("patterns") != ["*"]:
      return False
    if not changed:
      return False
    for path in changed:
      if path not in old_tree or path not in new_tree:
        return False
      before, after = data.blob(old_tree[path]), data.blob(new_tree[path])
      if ecosystem == "github-actions":
        if not re.fullmatch(
          r"\.github/workflows/[^/]+\.ya?ml", path
        ) or not dependency_workflow(before, after, names):
          return False
      elif ecosystem == "uv":
        if path == "pyproject.toml":
          if not dependency_manifest(before, after, names):
            return False
        elif path == "uv.lock":
          if not dependency_lock(before, after):
            return False
        else:
          return False
      else:
        return False
    return True
  except (
    m.MarketplaceError,
    yaml.YAMLError,
    KeyError,
    UnicodeError,
    TypeError,
    ValueError,
  ):
    return False
