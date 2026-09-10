#!/usr/bin/env python3
"""Scaffold, preview, and submit hosted marketplace Agent Skills."""

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
  "prompt": "reserved",
  "instructions": "reserved",
  "agent": "reserved",
  "hook": "deferred",
  "mcp": "deferred",
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


def _skill_dir(marketplace: Path, name: str, specialty: str = "community") -> Path:
  """Validate a skill name and return its canonical package directory."""
  if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
    raise CreateError("skill name must be kebab-case and at most 64 characters")
  if specialty not in {"community", "security"}:
    raise CreateError("specialty must be community or security")
  return marketplace.resolve() / "skills" / specialty / name


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


def _manifest(args) -> dict:
  """Build author-controlled marketplace metadata for a new package."""
  return {
    "schema-version": "bcgov-extension/v1alpha1",
    "id": f"bcgov-public/{args.name}",
    "display-name": args.display_name,
    "summary": args.summary,
    "publisher": "Province of British Columbia",
    "maintainers": args.maintainer,
    "support": args.support,
    "license": "Apache-2.0",
    "lifecycle": "active",
    "prerequisites": [],
    "capabilities": {
      "filesystem": {"read": [], "write": []},
      "network": [],
      "commands": [],
      "environment-variables": [],
      "secret-names": [],
      "data-classes": ["PUBLIC"],
    },
  }


def initialize(args) -> dict:
  """Create one new hosted skill package without overwriting existing work."""
  _require_active_type(getattr(args, "extension_type", "skill"))
  package = _skill_dir(args.marketplace, args.name, args.specialty)
  if package.exists():
    raise CreateError(f"package already exists: {package}")
  package.mkdir(parents=True)
  (package / "SKILL.md").write_text(
    _skill_template(args.name, args.description, args.display_name), encoding="utf-8"
  )
  (package / "bcgov-extension.yaml").write_text(
    yaml.safe_dump(_manifest(args), sort_keys=False, allow_unicode=False),
    encoding="utf-8",
  )
  return {"package": str(package), "files": ["SKILL.md", "bcgov-extension.yaml"]}


def _validate(marketplace: Path, name: str, specialty: str) -> list[dict]:
  """Run portable and marketplace gates without executing package scripts."""
  package = _skill_dir(marketplace, name, specialty)
  commands = [
    ["uv", "run", "python", "scripts/validate_skill.py", str(package / "SKILL.md")],
    ["uv", "run", "python", "scripts/marketplace.py", "analyze", str(package)],
    ["uv", "run", "python", "scripts/marketplace.py", "generate"],
    ["uv", "run", "pytest", "-q"],
    ["uv", "run", "python", "scripts/marketplace.py", "validate"],
  ]
  results = []
  for command in commands:
    results.append({"command": " ".join(command), "output": _run(command, marketplace)})
  return results


def _public_diff(marketplace: Path, name: str, specialty: str = "community") -> str:
  """Return tracked and untracked package and generated projection changes."""
  tracked = _run(
    [
      "git",
      "diff",
      "--",
      f"skills/{specialty}/{name}",
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
      f"skills/{specialty}/{name}",
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
  _require_active_type(getattr(args, "extension_type", "skill"))
  marketplace = args.marketplace.resolve()
  package = _skill_dir(marketplace, args.name, args.specialty)
  if not package.is_dir():
    raise CreateError(f"package does not exist: {package}")
  validation = _validate(marketplace, args.name, args.specialty)
  manifest = yaml.safe_load(
    (package / "bcgov-extension.yaml").read_text(encoding="utf-8")
  )
  changed = _run(["git", "status", "--short"], marketplace)
  diff = _public_diff(marketplace, args.name, args.specialty)
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
  _require_active_type(getattr(args, "extension_type", "skill"))
  marketplace = args.marketplace.resolve()
  package = _skill_dir(marketplace, args.name, args.specialty)
  if not package.is_dir():
    raise CreateError(f"package does not exist: {package}")
  current_branch = _run(["git", "branch", "--show-current"], marketplace)
  if current_branch in {"", "main"}:
    _run(["git", "switch", "-c", args.branch], marketplace)
  elif current_branch != args.branch:
    raise CreateError(f"checkout is on {current_branch!r}, expected {args.branch!r}")
  _validate(marketplace, args.name, args.specialty)
  allowed = (
    f"skills/{args.specialty}/{args.name}/",
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
      f"skills/{args.specialty}/{args.name}",
      "catalog/catalog.json",
      "docs/assets/catalog.json",
      "docs/_generated/catalog-cards.html",
    ],
    marketplace,
  )
  _run(["git", "commit", "-S", "-m", f"feat(skills): add {args.name}"], marketplace)
  commit = _run(["git", "rev-parse", "HEAD"], marketplace)
  _run(["git", "push", "--set-upstream", "origin", args.branch], marketplace)
  body = "\n".join(
    [
      "## Summary",
      f"Adds the `{args.name}` marketplace extension package.",
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
  initialize_parser.add_argument(
    "--specialty", choices=["community", "security"], default="community"
  )
  initialize_parser.add_argument(
    "--support", default="https://github.com/bcgov/agent-marketplace/issues"
  )
  preview_parser = commands.add_parser("preview")
  preview_parser.add_argument("--marketplace", type=Path, required=True)
  preview_parser.add_argument("--name", required=True)
  preview_parser.add_argument(
    "--extension-type", choices=sorted(EXTENSION_TYPE_STATUS), default="skill"
  )
  preview_parser.add_argument(
    "--specialty", choices=["community", "security"], default="community"
  )
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
  submit_parser.add_argument(
    "--specialty", choices=["community", "security"], default="community"
  )
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
