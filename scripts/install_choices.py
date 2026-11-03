"""Shared tested native placement choices; contributed files remain inert data."""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from pathlib import Path, PurePosixPath


class PlacementError(Exception):
  """Report a refused native file operation without changing existing guidance."""


def _safe_path(root: Path, relative: str) -> Path:
  """Reject paths that escape the selected directory or traverse symbolic links."""
  parts = PurePosixPath(relative).parts
  if (
    not parts
    or PurePosixPath(relative).is_absolute()
    or any(part in {"..", "."} or ":" in part or "\\" in part for part in parts)
  ):
    raise PlacementError("invalid relative placement path")
  target = root
  for index, part in enumerate(parts):
    target = target / part
    if target.is_symlink() or target.is_junction():
      raise PlacementError(f"destination collision: linked path {target}")
    if target.is_file() and target.stat().st_nlink > 1:
      raise PlacementError(f"destination collision: hard-linked file {target}")
    if index < len(parts) - 1 and target.exists() and not target.is_dir():
      raise PlacementError(f"destination collision: parent is a file {target}")
  if not target.resolve().is_relative_to(root.resolve()):
    raise PlacementError("placement escapes selected directory")
  return target


def verify_choice(choice: dict, project: Path) -> list[dict]:
  """Compare actual installed native bytes to the selected Catalogue file hashes."""
  _validate_layout(choice)
  results = []
  for item in choice["placements"]:
    target = _safe_path(project, item["destination"])
    actual = (
      hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    )
    results.append(
      {
        "destination": item["destination"],
        "expected": item["sha256"],
        "actual": actual,
        "valid": actual == item["sha256"],
      }
    )
  return results


def _validate_layout(choice: dict) -> None:
  """Confine Catalogue-driven writes to the canonical native destination map."""
  match = re.fullmatch(
    r"bcgov-public/(skill|instructions|prompt|agent)/([a-z0-9]+(?:-[a-z0-9]+)*)",
    choice.get("extension-id", ""),
  )
  if not match or (choice.get("id"), choice.get("scope")) not in {
    ("vscode-project", "project"),
    ("vscode-user-skill", "global"),
  }:
    raise PlacementError("unsupported native placement choice")
  kind, name = match.groups()
  if choice["scope"] == "global" and kind != "skill":
    raise PlacementError("global placement is tested for skills only")
  directory = {
    "skill": "skills",
    "instructions": "instructions",
    "prompt": "prompts",
    "agent": "agents",
  }[kind]
  filename = "SKILL.md" if kind == "skill" else f"{name}.{kind}.md"
  expected = (
    f".github/{directory}/{name}"
    if kind == "skill"
    else f".github/{directory}/{filename}"
  )
  if choice["scope"] == "global":
    expected = f".copilot/skills/{name}"
  if choice.get("destination") != expected or not choice.get("placements"):
    raise PlacementError("native destination does not match canonical identity")
  seen = set()
  for item in choice["placements"]:
    source = item["source"]
    destination = f"{expected}/{source}" if kind == "skill" else expected
    if (
      item["destination"] != destination
      or (kind != "skill" and source != filename)
      or source == "bcgov-extension.yaml"
      or destination.casefold() in seen
    ):
      raise PlacementError("invalid or colliding native placement map")
    seen.add(destination.casefold())


def remove_choice(choice: dict, project: Path, *, confirmed: bool = False) -> dict:
  """Delete only explicitly selected native files whose installed bytes match."""
  if not confirmed:
    raise PlacementError("removal requires explicit confirmation")
  if not all(item["valid"] for item in verify_choice(choice, project)):
    raise PlacementError("installed bytes changed; review and remove manually")
  removed = []
  for item in choice["placements"]:
    target = _safe_path(project, item["destination"])
    target.unlink()
    removed.append(item["destination"])
  # Remove only empty native package directories, never unrelated contents.
  if choice["extension-id"].split("/")[1] == "skill":
    destination = _safe_path(project, choice["destination"])
    directories = {destination}
    for item in choice["placements"]:
      parent = _safe_path(project, item["destination"]).parent
      while parent.is_relative_to(destination):
        directories.add(parent)
        parent = parent.parent
    for directory in sorted(
      directories, key=lambda item: len(item.parts), reverse=True
    ):
      if directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()
  return {"removed": removed}


def place_choice(
  choice: dict,
  package: Path,
  project: Path,
  *,
  confirmed: bool = False,
  previous: dict | None = None,
  allow_migration: bool = False,
) -> dict:
  """Copy a selected native layout with explicit consent and byte verification."""
  if not confirmed:
    raise PlacementError("placement requires explicit confirmation")
  _validate_layout(choice)
  old_destinations = set()
  if previous is not None:
    _validate_layout(previous)
    if (
      previous["extension-id"] != choice["extension-id"]
      or previous["scope"] != choice["scope"]
    ):
      raise PlacementError("cannot overwrite another Extension")
    if (
      any(
        previous["source"][key] != choice["source"][key]
        for key in ("repository", "path")
      )
      and not allow_migration
    ):
      raise PlacementError("source migration requires explicit --allow-migration")
    if not all(item["valid"] for item in verify_choice(previous, project)):
      raise PlacementError("installed bytes changed; review before replacement")
    old_destinations = {item["destination"] for item in previous["placements"]}
  destination = _safe_path(project, choice["destination"])
  if previous is None and destination.exists():
    raise PlacementError(f"destination collision: {destination}")
  copies = []
  for item in choice["placements"]:
    source = _safe_path(package, item["source"])
    target = _safe_path(project, item["destination"])
    if target.exists() and item["destination"] not in old_destinations:
      raise PlacementError(f"destination collision: {target}")
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != item["sha256"]:
      raise PlacementError("downloaded native bytes differ from the Catalogue")
    copies.append((target, content))
  for target, content in copies:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open(
      "wb" if target.relative_to(project).as_posix() in old_destinations else "xb"
    ) as stream:
      stream.write(content)
  new_destinations = {item["destination"] for item in choice["placements"]}
  for old in old_destinations - new_destinations:
    _safe_path(project, old).unlink()
  verified = verify_choice(choice, project)
  if not all(item["valid"] for item in verified):
    raise PlacementError("post-copy native byte comparison failed")
  return {
    "installed": [str(project / item["destination"]) for item in verified],
    "verified": True,
    "installer": choice["installer"],
    "scope": choice["scope"],
    "source": choice["source"],
    "canonical-id": choice["extension-id"],
  }


def build_install_choices(record: dict, package: Path) -> list[dict]:
  """Offer only tested VS Code Local project layouts for actual native content."""
  from marketplace import read_native_content

  kind = record.get("type")
  identity = record.get("id", "")
  match = re.fullmatch(
    r"bcgov-public/(skill|instructions|prompt|agent)/([a-z0-9]+(?:-[a-z0-9]+)*)",
    identity,
  )
  if record.get("lifecycle") != "active" or not match or match[1] != kind:
    return []
  if "vscode" in record.get("compatibility", {}).get("not-ready-on", []):
    return []
  name = match[2]
  filename = "SKILL.md" if kind == "skill" else f"{name}.{kind}.md"
  frontmatter, errors = read_native_content(package / filename, kind)
  if errors:
    return []
  if (
    kind == "instructions"
    and "applyTo" in frontmatter
    and not isinstance(frontmatter["applyTo"], str)
  ):
    return []
  if kind == "agent" and frontmatter.get("target", "vscode") != "vscode":
    return []
  if kind in {"agent", "prompt"} and "tools" in frontmatter:
    tools = frontmatter["tools"]
    if not isinstance(tools, (str, list)) or (
      isinstance(tools, list) and not all(isinstance(tool, str) for tool in tools)
    ):
      return []
  if kind == "skill" and (
    frontmatter.get("name") != name
    or len(name) > 64
    or not isinstance(frontmatter.get("description"), str)
    or not 1 <= len(frontmatter["description"].strip()) <= 1024
    or any(char in frontmatter["description"] for char in "<>")
  ):
    return []
  source = record["source"]
  if not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
    return []
  if not re.fullmatch(
    r"https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source["repository"]
  ):
    return []
  path = PurePosixPath(source["path"])
  if path.is_absolute() or ".." in path.parts or not path.parts:
    return []
  directory = {
    "skill": "skills",
    "instructions": "instructions",
    "prompt": "prompts",
    "agent": "agents",
  }[kind]
  if len(path.parts) != 3 or path.parts[0] != directory or path.name != name:
    return []
  files = sorted(
    (item for item in package.rglob("*") if item.is_file()),
    key=lambda item: item.relative_to(package).as_posix(),
  )
  if any(item.is_symlink() for item in package.rglob("*")):
    return []
  files = [item for item in files if item.name != "bcgov-extension.yaml"]
  # Flattening arbitrary relative references needs a separate tested adaptation.
  if kind != "skill" and files != [package / filename]:
    return []
  destination = (
    f".github/{directory}/{name}"
    if kind == "skill"
    else f".github/{directory}/{filename}"
  )
  placements = []
  for item in files:
    relative = item.relative_to(package).as_posix()
    placements.append(
      {
        "source": relative,
        "destination": f"{destination}/{relative}" if kind == "skill" else destination,
        "sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
      }
    )
  choices = [
    {
      "id": "vscode-project",
      "extension-id": identity,
      "client": "VS Code Local",
      "installer": "manual",
      "scope": "project",
      "destination-root": "project",
      "source": dict(source),
      "source-label": "Catalogue source",
      "source-url": (
        f"{source['repository']}/tree/{source['revision']}/{source['path']}"
      ),
      "latest-source": {
        "label": "latest source",
        "url": f"{source['repository']}/tree/main/{source['path']}",
      },
      "destination": destination,
      "placements": placements,
      "install": (
        "Download the full-SHA source. Inspect every destination and collision; "
        "explicitly copy only the mapped native files. Keep skill resources "
        "together. Do not copy the marketplace Manifest."
      ),
      "update": (
        "Select the desired published SHA, compare source and installed bytes, "
        "then explicitly replace mapped files. A Specialty path transfer needs "
        "explicit source migration; aliases never authorize an overwrite."
      ),
      "remove": (
        "Inspect mapped destinations, then explicitly delete those files only. "
        "Preserve unrelated guidance."
      ),
      "integrity": (
        "A SHA URL pins source; manual download does not verify bytes. Compare "
        "each downloaded and installed file with its listed SHA-256. The "
        "repository helper performs these comparisons."
      ),
      "evidence": {
        "contract": "native-project-layout/v1",
        "tested": "fixture placement and byte comparisons",
        "runtime-evaluation": False,
      },
    }
  ]
  if kind == "skill":
    personal = deepcopy(choices[0])
    personal.update(
      {
        "id": "vscode-user-skill",
        "scope": "global",
        "destination-root": "home",
        "destination": f".copilot/skills/{name}",
      }
    )
    for item in personal["placements"]:
      item["destination"] = item["destination"].replace(
        ".github/skills/", ".copilot/skills/", 1
      )
    personal["install"] = (
      "Select your home directory explicitly. " + personal["install"]
    )
    choices.append(personal)
  return choices
