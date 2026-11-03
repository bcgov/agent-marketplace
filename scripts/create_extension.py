#!/usr/bin/env python3
"""Scaffold, preview, and submit hosted marketplace agent assets."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


class CreateError(Exception):
  """Represent an authoring or submission error safe to show to the user."""


EXTENSION_TYPE_STATUS = {
  "skill": "active",
  "prompt": "active",
  "instructions": "active",
  "agent": "active",
  "hook": "deferred",
  "mcp": "deferred",
}
TYPE_DIRECTORIES = {
  "skill": "skills",
  "prompt": "prompts",
  "instructions": "instructions",
  "agent": "agents",
}
ARTIFACT_FILENAMES = {
  "skill": "SKILL.md",
  "prompt": "{name}.prompt.md",
  "instructions": "{name}.instructions.md",
  "agent": "{name}.agent.md",
}


def _require_active_type(extension_type: str) -> None:
  """Reject types without a complete marketplace adapter."""
  status = EXTENSION_TYPE_STATUS.get(extension_type)
  if status is None:
    raise CreateError(f"unsupported extension type: {extension_type}")
  if status != "active":
    raise CreateError(
      f"extension type {extension_type!r} is {status}; scaffolding is unavailable"
    )


def _run(command: list[str], cwd: Path, capture: bool = True) -> str:
  """Run one bounded repository command and return standard output."""
  try:
    result = subprocess.run(
      command,
      cwd=cwd,
      check=True,
      text=True,
      stdout=subprocess.PIPE if capture else None,
      stderr=subprocess.PIPE if capture else None,
    )
  except FileNotFoundError as exc:
    raise CreateError(f"required command is not installed: {command[0]}") from exc
  except subprocess.CalledProcessError as exc:
    detail = (exc.stderr or exc.stdout or str(exc)).strip()
    raise CreateError(f"command failed ({' '.join(command)}): {detail}") from exc
  return result.stdout.strip() if capture else ""


def _package_dir(
  marketplace: Path, name: str, extension_type: str, specialty: str = "community"
) -> Path:
  """Validate package metadata and return its canonical asset directory."""
  if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
    raise CreateError("extension name must be kebab-case and at most 64 characters")
  _require_active_type(extension_type)
  registry = marketplace / "config" / "specialties.yaml"
  if not registry.exists():
    registry = Path(__file__).resolve().parents[1] / "config" / "specialties.yaml"
  choices = {
    item["id"]
    for item in yaml.safe_load(registry.read_text(encoding="utf-8"))["specialties"]
  }
  if specialty not in {"community", *choices}:
    raise CreateError(f"specialty must be community or one of {sorted(choices)}")
  return marketplace.resolve() / TYPE_DIRECTORIES[extension_type] / specialty / name


def _skill_template(name: str, description: str, display_name: str) -> str:
  """Render a portable SKILL.md authoring template."""
  return f"""---
name: {name}
description: {description}
owner: bcgov
tags: [bcgov]
license: Apache-2.0
---

# {display_name}

## Use When
- Describe the specific request that should route here.

## Don't Use When
- Describe the adjacent case and point to the better skill or resource.

## Workflow
1. Describe the first observable action.
2. Validate the result before proceeding.

## Rules
- Always state the safety or correctness boundary and why it matters.

## Examples
- \"Example request\" -> describe the concrete response.

## Edge Cases
- If required context is missing -> ask for the smallest missing input.

## References
Add public supporting detail under `references/` and link it here, or state that
no bundled references are required.
"""


def _artifact_template(
  extension_type: str, name: str, description: str, display_name: str
) -> str:
  """Render a portable starter file for one supported agent asset type."""
  if extension_type == "skill":
    return _skill_template(name, description, display_name)
  frontmatter = {"description": description}
  if extension_type in {"prompt", "agent"}:
    frontmatter["name"] = name
  if extension_type == "prompt":
    frontmatter["agent"] = "agent"
  serialized = yaml.safe_dump(
    frontmatter, sort_keys=False, allow_unicode=False
  ).rstrip()
  body = {
    "prompt": (
      "Describe the user input, evidence to inspect, and one bounded deliverable."
    ),
    "instructions": (
      "State the persistent guidance, its scope, and any important exceptions."
    ),
    "agent": (
      "Define one focused responsibility, operating boundaries, and "
      "completion criteria."
    ),
  }[extension_type]
  return f"---\n{serialized}\n---\n\n# {display_name}\n\n{body}\n"


def _manifest(args) -> dict:
  """Build author-controlled marketplace metadata for a new package."""
  manifest = {"maintainers": args.maintainer, "capabilities": "none"}
  if args.display_name != args.name:
    manifest["display-name"] = args.display_name
  if args.summary != args.description:
    manifest["summary"] = args.summary
  if (
    getattr(args, "support", "https://github.com/bcgov/agent-marketplace/issues")
    != "https://github.com/bcgov/agent-marketplace/issues"
  ):
    manifest["support"] = args.support
  if getattr(args, "not_ready_on", []):
    manifest["compatibility"] = {"not-ready-on": args.not_ready_on}
  return manifest


def initialize(args) -> dict:
  """Create one new hosted asset package without overwriting existing work."""
  extension_type = getattr(args, "extension_type", "skill")
  marketplace = args.marketplace.resolve()
  package = _package_dir(marketplace, args.name, extension_type, args.specialty)
  if any((marketplace / TYPE_DIRECTORIES[extension_type]).glob(f"*/{args.name}")):
    raise CreateError(
      f"extension id is already in use: bcgov-public/{extension_type}/{args.name}"
    )
  package.mkdir(parents=True)
  artifact_filename = ARTIFACT_FILENAMES[extension_type].format(name=args.name)
  (package / artifact_filename).write_text(
    _artifact_template(extension_type, args.name, args.description, args.display_name),
    encoding="utf-8",
  )
  (package / "bcgov-extension.yaml").write_text(
    yaml.safe_dump(_manifest(args), sort_keys=False, allow_unicode=False),
    encoding="utf-8",
  )
  return {
    "package": str(package),
    "files": [artifact_filename, "bcgov-extension.yaml"],
  }


def _validate(
  marketplace: Path, name: str, specialty: str, extension_type: str = "skill"
) -> list[dict]:
  """Run portable and marketplace gates without executing package scripts."""
  package = _package_dir(marketplace, name, extension_type, specialty)
  commands = []
  if extension_type == "skill":
    commands.append(
      ["uv", "run", "python", "scripts/validate_skill.py", str(package / "SKILL.md")]
    )
  commands.extend(
    [
      ["uv", "run", "python", "scripts/marketplace.py", "analyze", str(package)],
      ["uv", "run", "python", "scripts/marketplace.py", "generate"],
      ["uv", "run", "pytest", "-q", "tests/"],
      ["uv", "run", "python", "scripts/marketplace.py", "validate"],
    ]
  )
  results = []
  for command in commands:
    results.append({"command": " ".join(command), "output": _run(command, marketplace)})
  return results


def _public_diff(marketplace: Path, package_path: str) -> str:
  """Return tracked and untracked package and generated projection changes."""
  tracked = _run(
    [
      "git",
      "diff",
      "--",
      package_path,
      "catalog",
      "docs/_generated",
      "docs/assets/catalog.json",
    ],
    marketplace,
  )
  untracked = _run(
    [
      "git",
      "ls-files",
      "--others",
      "--exclude-standard",
      "--",
      package_path,
    ],
    marketplace,
  )
  patches = [tracked] if tracked else []
  for relative_path in untracked.splitlines():
    result = subprocess.run(
      ["git", "diff", "--no-index", "--", "/dev/null", relative_path],
      cwd=marketplace,
      check=False,
      text=True,
      capture_output=True,
    )
    if result.returncode not in {0, 1}:
      detail = (result.stderr or result.stdout).strip()
      raise CreateError(f"cannot preview untracked file {relative_path}: {detail}")
    if result.stdout.strip():
      patches.append(result.stdout.strip())
  return "\n\n".join(patches)


def preview(args) -> dict:
  """Validate and return the complete public package preview."""
  extension_type = getattr(args, "extension_type", "skill")
  marketplace = args.marketplace.resolve()
  package = _package_dir(marketplace, args.name, extension_type, args.specialty)
  if not package.is_dir():
    raise CreateError(f"package does not exist: {package}")
  validation = _validate(marketplace, args.name, args.specialty, extension_type)
  manifest = yaml.safe_load(
    (package / "bcgov-extension.yaml").read_text(encoding="utf-8")
  )
  changed = _run(["git", "status", "--short"], marketplace)
  diff = _public_diff(marketplace, package.relative_to(marketplace).as_posix())
  files = [
    path.relative_to(package).as_posix()
    for path in sorted(package.rglob("*"))
    if path.is_file()
  ]
  return {
    "destination": "https://github.com/bcgov/agent-marketplace",
    "package": str(package),
    "files": files,
    "capabilities": manifest["capabilities"],
    "compatibility": manifest.get("compatibility", {"not-ready-on": []}),
    "validation": validation,
    "working-tree": changed,
    "diff": diff,
  }


def _confirm(assume_yes: bool) -> None:
  """Require one explicit submission confirmation unless already obtained."""
  if (
    not assume_yes
    and input("Create a signed commit, push, and open a draft PR? Type 'yes': ")
    .strip()
    .lower()
    != "yes"
  ):
    raise CreateError("submission cancelled")


def submit(args) -> dict:
  """Create a signed package commit and open a draft pull request."""
  extension_type = getattr(args, "extension_type", "skill")
  marketplace = args.marketplace.resolve()
  package = _package_dir(marketplace, args.name, extension_type, args.specialty)
  if not package.is_dir():
    raise CreateError(f"package does not exist: {package}")
  current_branch = _run(["git", "branch", "--show-current"], marketplace)
  if current_branch in {"", "main"}:
    _run(["git", "switch", "-c", args.branch], marketplace)
  elif current_branch != args.branch:
    raise CreateError(f"checkout is on {current_branch!r}, expected {args.branch!r}")
  _validate(marketplace, args.name, args.specialty, extension_type)
  package_path = package.relative_to(marketplace).as_posix()
  allowed = (
    f"{package_path}/",
    "catalog/catalog.json",
    "docs/assets/catalog.json",
    "docs/_generated/catalog-cards.html",
  )
  changed = _run(["git", "status", "--porcelain"], marketplace).splitlines()
  unexpected = []
  for line in changed:
    path = line[3:].split(" -> ")[-1]
    if not any(
      path == prefix.rstrip("/") or path.startswith(prefix) for prefix in allowed
    ):
      unexpected.append(path)
  if unexpected:
    raise CreateError("checkout contains unrelated changes: " + ", ".join(unexpected))
  _confirm(args.yes)
  _run(
    [
      "git",
      "add",
      package_path,
      "catalog/catalog.json",
      "docs/assets/catalog.json",
      "docs/_generated/catalog-cards.html",
    ],
    marketplace,
  )
  _run(
    [
      "git",
      "commit",
      "-S",
      "-m",
      f"feat(extensions): add {args.name}",
    ],
    marketplace,
  )
  commit = _run(["git", "rev-parse", "HEAD"], marketplace)
  _run(["git", "push", "--set-upstream", "origin", args.branch], marketplace)
  body = "\n".join(
    [
      "## Summary",
      f"Adds the `{args.name}` {extension_type} marketplace extension package.",
      "",
      "## Upstream search",
      args.upstream_evidence,
      "",
      "## Validation",
      "Generated and validated by `bcgov-create-extension`.",
      f"Exact submitted revision: `{commit}`",
    ]
  )
  url = _run(
    [
      "gh",
      "pr",
      "create",
      "--draft",
      "--repo",
      "bcgov/agent-marketplace",
      "--base",
      "main",
      "--head",
      args.branch,
      "--title",
      args.title,
      "--body",
      body,
    ],
    marketplace,
  )
  return {"commit": commit, "pull-request": url, "draft": True}


def _parser() -> argparse.ArgumentParser:
  """Build the creation companion command-line parser."""
  parser = argparse.ArgumentParser(description=__doc__)
  commands = parser.add_subparsers(dest="command", required=True)
  initialize_parser = commands.add_parser("init")
  initialize_parser.add_argument("--marketplace", type=Path, required=True)
  initialize_parser.add_argument("--name", required=True)
  initialize_parser.add_argument(
    "--extension-type", choices=sorted(EXTENSION_TYPE_STATUS), default="skill"
  )
  initialize_parser.add_argument("--description", required=True)
  initialize_parser.add_argument("--display-name", required=True)
  initialize_parser.add_argument("--summary", required=True)
  initialize_parser.add_argument("--maintainer", action="append", required=True)
  initialize_parser.add_argument("--not-ready-on", action="append", default=[])
  initialize_parser.add_argument("--specialty", default="community")
  initialize_parser.add_argument(
    "--support", default="https://github.com/bcgov/agent-marketplace/issues"
  )
  preview_parser = commands.add_parser("preview")
  preview_parser.add_argument("--marketplace", type=Path, required=True)
  preview_parser.add_argument("--name", required=True)
  preview_parser.add_argument(
    "--extension-type", choices=sorted(EXTENSION_TYPE_STATUS), default="skill"
  )
  preview_parser.add_argument("--specialty", default="community")
  submit_parser = commands.add_parser("submit")
  submit_parser.add_argument("--marketplace", type=Path, required=True)
  submit_parser.add_argument("--name", required=True)
  submit_parser.add_argument(
    "--extension-type", choices=sorted(EXTENSION_TYPE_STATUS), default="skill"
  )
  submit_parser.add_argument("--branch", required=True)
  submit_parser.add_argument("--title", required=True)
  submit_parser.add_argument("--upstream-evidence", required=True)
  submit_parser.add_argument("--yes", action="store_true")
  submit_parser.add_argument("--specialty", default="community")
  return parser


def main(argv: list[str] | None = None) -> int:
  """Run one authoring command and return its process status."""
  args = _parser().parse_args(argv)
  try:
    if args.command == "init":
      result = initialize(args)
    elif args.command == "preview":
      result = preview(args)
    else:
      result = submit(args)
    print(json.dumps(result, indent=2, sort_keys=True))
  except CreateError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
