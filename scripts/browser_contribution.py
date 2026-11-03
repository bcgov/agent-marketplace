#!/usr/bin/env python3
"""Build inert browser authoring data from the registry and native templates."""

import argparse
import json
from pathlib import Path

from create_extension import ARTIFACT_FILENAMES, TYPE_DIRECTORIES, native_template
from marketplace import load_specialties, manifest_paths


def build(root: Path) -> dict:
  """Describe the two-file starter without requiring derived Catalogue output."""
  kinds = {directory: kind for kind, directory in TYPE_DIRECTORIES.items()}
  return {
    "specialties": [
      {
        "id": "community",
        "display-name": "Community",
        "description": (
          "General-purpose Extensions. Start here unless a Specialty fits."
        ),
        "owner-team": None,
        "review-rule": "community",
      },
      *load_specialties(root),
    ],
    "types": {
      kind: {
        "directory": directory,
        "filename": ARTIFACT_FILENAMES[kind],
        "native": native_template(
          kind, "__EXTENSION_NAME__", "__SUMMARY__", "__EXTENSION_NAME__"
        ),
      }
      for kind, directory in TYPE_DIRECTORIES.items()
    },
    "reserved": sorted(
      f"bcgov-public/{kinds[path.parts[-4]]}/{path.parts[-2]}"
      for path in manifest_paths(root)
    ),
  }


def main() -> None:
  """Write transient site data, including newly registered Specialties."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
  parser.add_argument("--output", type=Path)
  args = parser.parse_args()
  target = args.output or args.root / "docs/assets/contribute.json"
  target.parent.mkdir(parents=True, exist_ok=True)
  target.write_text(json.dumps(build(args.root), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
  main()
