#!/usr/bin/env python3
"""Run safe, repeatable marketplace demonstration scenarios."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import marketplace
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs" / "demos" / "fixtures"


def _fixture_path(name: str) -> Path:
  """Resolve one checked-in demo fixture."""
  path = FIXTURES / name
  if not path.is_dir():
    raise ValueError(f"unknown demo fixture: {name}")
  return path


def analyze_fixture(name: str) -> dict:
  """Analyze a fixture in an isolated canonical package path."""
  fixture = _fixture_path(name)
  package = Path(
    tempfile.mkdtemp(
      prefix="demo-submission-",
      dir=ROOT / "skills" / "community",
    )
  )
  try:
    shutil.copytree(fixture, package, dirs_exist_ok=True)
    manifest_path = package / marketplace.MANIFEST_NAME
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["id"] = f"bcgov-public/{package.name}"
    manifest_path.write_text(
      yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    result = marketplace.analyze_submission(ROOT, package)
    result["fixture"] = name
    return result
  finally:
    shutil.rmtree(package)


def main(argv: list[str] | None = None) -> int:
  """Run one demonstration scenario and print stable JSON evidence."""
  parser = argparse.ArgumentParser(description=__doc__)
  commands = parser.add_subparsers(dest="command", required=True)
  analyze_parser = commands.add_parser(
    "analyze-fixture", help="scan a fixture without executing its content"
  )
  analyze_parser.add_argument(
    "fixture", choices=("benign-submission", "blocked-submission")
  )
  args = parser.parse_args(argv)
  if args.command == "analyze-fixture":
    print(json.dumps(analyze_fixture(args.fixture), indent=2, sort_keys=True))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
