#!/usr/bin/env python3
"""Independently rescan one federated candidate issue without executing it."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[1]
FINDER_PATH = ROOT / "scripts" / "find_extension.py"


class CandidateError(Exception):
  """Represent invalid or unverifiable candidate intake."""


def _finder():
  """Load the trusted finder scanner from this marketplace checkout."""
  spec = importlib.util.spec_from_file_location("candidate_finder", FINDER_PATH)
  if spec is None or spec.loader is None:
    raise CandidateError("cannot load the candidate scanner")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def parse_issue(body: str) -> dict[str, str]:
  """Parse values from a GitHub issue-form body by exact field heading."""
  fields = {}
  pattern = re.compile(r"^### (.+?)\n\n(.*?)(?=\n\n### |\Z)", re.MULTILINE | re.DOTALL)
  for match in pattern.finditer(body.replace("\r\n", "\n")):
    fields[match.group(1).strip()] = match.group(2).strip()
  required = [
    "Discovery catalog",
    "Source repository",
    "Full commit SHA",
    "Package path",
    "Declared capabilities",
  ]
  missing = [
    name for name in required if not fields.get(name) or fields[name] == "_No response_"
  ]
  if missing:
    raise CandidateError("missing issue fields: " + ", ".join(missing))
  return fields


def approved_catalogs() -> set[str]:
  """Return catalogs configured as approved discovery sources."""
  config = yaml.safe_load((ROOT / "config" / "marketplace.yaml").read_text())
  return {
    source["catalog"].rstrip("/")
    for source in config.get("approved-discovery-sources", [])
  }


def verify(body: str) -> tuple[dict, bool]:
  """Resolve and scan a candidate, comparing an optional claimed digest."""
  fields = parse_issue(body)
  discovery_catalog = fields["Discovery catalog"].rstrip("/")
  if discovery_catalog not in approved_catalogs():
    raise CandidateError("discovery catalog is not an approved discovery source")
  repository = fields["Source repository"].rstrip("/")
  revision = fields["Full commit SHA"].strip("` ")
  package_path = fields["Package path"].strip("` ")
  expected = fields.get("Package-tree digest", "").strip("` ")
  if expected == "_No response_":
    expected = ""
  if expected and not re.fullmatch(r"sha256:[0-9a-f]{64}", expected):
    raise CandidateError(
      "package-tree digest must be sha256 followed by 64 lowercase hex characters"
    )
  capabilities_text = fields["Declared capabilities"]
  capabilities_text = re.sub(r"^```(?:json)?\s*", "", capabilities_text)
  capabilities_text = re.sub(r"\s*```$", "", capabilities_text)
  try:
    capabilities = json.loads(capabilities_text)
  except json.JSONDecodeError as exc:
    raise CandidateError(f"declared capabilities must be valid JSON: {exc}") from exc
  if not isinstance(capabilities, dict):
    raise CandidateError("declared capabilities must be a JSON object")
  scanner = _finder()
  result = scanner._scan_source(
    SimpleNamespace(
      repository=repository,
      revision=revision,
      path=package_path,
      capabilities=capabilities,
    )
  )
  result["discovery-catalog"] = discovery_catalog
  digest_match = result["package-tree-digest"] == expected if expected else None
  valid = digest_match is not False and result["scan"]["outcome"] == "passed"
  result["expected-package-tree-digest"] = expected or None
  result["digest-match"] = digest_match
  return result, valid


def render_report(result: dict | None, error: str | None = None) -> str:
  """Render a stable issue comment containing independent rescan evidence."""
  lines = ["## Independent marketplace rescan", ""]
  if error:
    lines.extend(["**Outcome: blocked**", "", error])
  else:
    outcome = (
      "passed"
      if result
      and result["digest-match"] is not False
      and result["scan"]["outcome"] == "passed"
      else "blocked"
    )
    lines.extend([f"**Outcome: {outcome}**", ""])
    if result["expected-package-tree-digest"]:
      lines.extend(
        [
          f"- Expected digest: `{result['expected-package-tree-digest']}`",
          f"- Digest match: `{str(result['digest-match']).lower()}`",
        ]
      )
    lines.extend(
      [
        f"- Reproduced digest: `{result['package-tree-digest']}`",
        f"- Policy: `{result['scan']['policy-version']}`",
        f"- Scanner outcome: `{result['scan']['outcome']}`",
        "",
        "```json",
        json.dumps(result["scan"]["findings"], indent=2, sort_keys=True),
        "```",
      ]
    )
  lines.extend(
    [
      "",
      "Candidate content was treated as data and was not executed.",
      "",
      "<!-- marketplace-independent-rescan -->",
    ]
  )
  return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
  """Read an issue body, write a report, and return pass/fail status."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--body-env", default="ISSUE_BODY")
  parser.add_argument("--output", type=Path, default=Path("candidate-report.md"))
  args = parser.parse_args(argv)
  try:
    result, valid = verify(os.environ.get(args.body_env, ""))
    report = render_report(result)
  except (CandidateError, OSError, ValueError, json.JSONDecodeError) as exc:
    valid = False
    report = render_report(None, str(exc))
  args.output.write_text(report, encoding="utf-8")
  return 0 if valid else 1


if __name__ == "__main__":
  sys.exit(main())
