"""Exercise validation workflow decisions using local event and command facts."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def _github_expression(template, context):
  """Render workflow property lookups and fallback expressions with event facts."""

  def value(match):
    """Resolve the first truthy property using GitHub's fallback semantics."""
    for property_path in match[1].split("||"):
      current = context
      for part in property_path.strip().split("."):
        current = current.get(part) if isinstance(current, dict) else None
      if current:
        return str(current)
    return ""

  return re.sub(r"\$\{\{\s*(.*?)\s*\}\}", value, template)


def _pr_event(number, fork, revision="a", repository="bcgov/agent-marketplace"):
  """Return two forks' ordinary same-branch GitHub pull request event facts."""
  return {
    "github": {
      "repository": repository,
      "head_ref": "patch-1",
      "ref": f"refs/pull/{number}/merge",
      "event": {
        "pull_request": {
          "number": number,
          "head": {"sha": revision * 40, "repo": {"full_name": fork}},
        }
      },
    }
  }


def test_pr_concurrency_isolates_forks_and_supersedes_only_the_same_pr():
  """Same-named fork branches are independent; new heads cancel their own PR."""
  workflow = yaml.safe_load((ROOT / ".github/workflows/pr.yml").read_text())
  concurrency = workflow["concurrency"]
  first = _github_expression(concurrency["group"], _pr_event(61, "alice/marketplace"))
  second = _github_expression(concurrency["group"], _pr_event(62, "bob/marketplace"))
  updated = _github_expression(
    concurrency["group"], _pr_event(61, "alice/marketplace", revision="b")
  )
  other_repository = _github_expression(
    concurrency["group"], _pr_event(61, "alice/marketplace", repository="other/repo")
  )
  assert first != second
  assert updated == first
  assert other_repository != first
  assert concurrency["cancel-in-progress"] is True
  fallback = {
    "github": {"repository": "bcgov/agent-marketplace", "ref": "refs/heads/main"}
  }
  assert _github_expression(concurrency["group"], fallback) != first
  assert "refs/heads/main" in _github_expression(concurrency["group"], fallback)
