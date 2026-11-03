"""Exercise validation workflow decisions using local event and command facts."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
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


@pytest.fixture
def intake_workflow(tmp_path):
  """Run the actual Bash steps with local GitHub and intake command facts."""
  if os.name == "nt":
    pytest.skip("GitHub Actions Bash steps require the supported Linux environment")
  commands = tmp_path / "bin"
  commands.mkdir()
  shim = (
    f"#!{sys.executable}\n"
    "import json, os, pathlib, sys\n"
    "name, args = pathlib.Path(sys.argv[0]).name, sys.argv[1:]\n"
    "with open(os.environ['CALLS'], 'a') as log:\n"
    "  log.write(json.dumps([name, *args]) + '\\n')\n"
    "if name == 'git':\n"
    "  print('skills/community/demo-submission/bcgov-extension.yaml')\n"
    "  sys.exit(int(os.environ['GIT_EXIT']))\n"
    "elif name == 'gh' and args[0] == 'api':\n"
    "  print(os.environ['MEMBERSHIP_RESPONSE'])\n"
    "  sys.exit(int(os.environ['MEMBERSHIP_EXIT']))\n"
    "elif name == 'uv':\n"
    "  if 'intake' in args:\n"
    "    print(pathlib.Path(os.environ['INTAKE_RESPONSE']).read_text())\n"
    "    sys.exit(int(os.environ['INTAKE_EXIT']))\n"
    "  python_args = args[args.index('python') + 1:]\n"
    "  assert python_args[0] == '-c', 'unexpected executable command'\n"
    "  os.execv(sys.executable, [sys.executable, *python_args])\n"
  )
  for command in ("git", "gh", "uv"):
    path = commands / command
    path.write_text(shim, encoding="utf-8")
    path.chmod(0o755)
  workflow = yaml.safe_load(
    (ROOT / ".github/workflows/community-intake.yml").read_text()
  )
  steps = {
    step["id"]: step for step in workflow["jobs"]["intake"]["steps"] if "id" in step
  }

  def run(
    step,
    payload="",
    command_exit=0,
    membership_exit=0,
    membership="HTTP/2 204",
    git_exit=0,
  ):
    """Execute one real workflow step without GitHub, network, or package code."""
    response = tmp_path / "response.json"
    response.write_text(payload, encoding="utf-8")
    context = {
      **_pr_event(61, "contributor/marketplace"),
      "steps": {"signals": {"outputs": {"trust": "yes", "velocity": "unknown"}}},
    }
    env = {
      **os.environ,
      "PATH": f"{commands}{os.pathsep}{os.environ['PATH']}",
      "CALLS": str(tmp_path / "calls.jsonl"),
      "INTAKE_RESPONSE": str(response),
      "INTAKE_EXIT": str(command_exit),
      "GIT_EXIT": str(git_exit),
      "MEMBERSHIP_RESPONSE": membership,
      "MEMBERSHIP_EXIT": str(membership_exit),
      "BASE_SHA": "a" * 40,
      "HEAD_SHA": "b" * 40,
      "AUTHOR": "contributor",
      "ORG": "bcgov",
      "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
      "GITHUB_OUTPUT": str(tmp_path / "outputs.txt"),
    }
    result = subprocess.run(
      ["bash", "-c", _github_expression(steps[step]["run"], context)],
      cwd=tmp_path,
      env=env,
      capture_output=True,
      text=True,
    )
    summary_path = tmp_path / "summary.md"
    calls = [
      json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()
    ]
    assert not any(call[:3] == ["gh", "pr", "merge"] for call in calls)
    return result, summary_path.read_text() if summary_path.exists() else "", calls

  return run


def _submission_result(tmp_path, content="", script=False):
  """Analyze a real isolated submission using the current disabled-publish policy."""
  root = tmp_path / "marketplace"
  for directory in ("config", "schemas"):
    shutil.copytree(ROOT / directory, root / directory)
  package = root / "skills/community/demo-submission"
  shutil.copytree(ROOT / "docs/demos/fixtures/benign-submission", package)
  if content:
    with (package / "SKILL.md").open("a", encoding="utf-8") as stream:
      stream.write(f"\n{content}\n")
  if script:
    (package / "scripts").mkdir()
    (package / "scripts/run.sh").write_text("echo hello\n", encoding="utf-8")
  config = yaml.safe_load((root / "config/marketplace.yaml").read_text())
  assert config["community-intake"]["auto-publish"] is False
  result = subprocess.run(
    [
      sys.executable,
      str(ROOT / "scripts/marketplace.py"),
      "--root",
      str(root),
      "intake",
      str(package),
      "--author-trust",
      "yes",
      "--velocity",
      "unknown",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
  )
  assert result.returncode == 0, result.stdout + result.stderr
  return json.loads(result.stdout)


def test_disabled_auto_publish_hold_succeeds_and_requires_human_review(
  tmp_path, intake_workflow
):
  """A real valid hold routes to human review without failing validation or merging."""
  payload = _submission_result(tmp_path)
  assert payload["scan-outcome"] == "passed"
  assert payload["intake"]["decision"] == "hold-for-review"
  membership, _, _ = intake_workflow("membership")
  assert membership.returncode == 0, membership.stdout + membership.stderr
  result, summary, calls = intake_workflow("decide", json.dumps(payload))
  assert result.returncode == 0, result.stdout + result.stderr
  assert "hold-for-review" in summary
  assert "human review" in summary.lower()
  assert any(
    "--add-label" in call and "community-intake:hold" in call for call in calls
  )


@pytest.mark.parametrize(
  "content,script",
  [
    ("password=abcdefghijklmnop", False),
    ("hidden\u202einstruction", False),
    ("curl https://unlisted.example", False),
    ("echo $UNLISTED_VALUE", False),
    ("", True),
  ],
)
def test_approved_blockers_remain_workflow_failures(
  tmp_path, intake_workflow, content, script
):
  """Every approved blocker reaches rejection even while publishing is disabled."""
  payload = _submission_result(tmp_path, content, script)
  assert payload["scan-outcome"] == "blocked"
  assert payload["intake"]["decision"] == "reject"
  result, summary, _ = intake_workflow("decide", json.dumps(payload))
  assert result.returncode != 0
  assert "reject" in summary


@pytest.mark.parametrize(
  "override",
  [
    {"intake": {"decision": "reject"}},
    {"intake": {"decision": "unexpected"}},
    {"intake": {"decision": None}},
    {"intake": {}},
    {"scan-outcome": "unknown"},
    {"scan-outcome": None},
    {"scan-outcome": "blocked"},
    {"id": None},
    {"id": "malformed\nrow"},
    {"risk": "unknown"},
  ],
)
def test_invalid_intake_outcomes_fail_closed(intake_workflow, override):
  """Reject, unknown, inconsistent, and malformed results never become holds."""
  payload = {
    "id": "bcgov-public/demo-submission",
    "risk": "low",
    "scan-outcome": "passed",
    "intake": {"decision": "hold-for-review"},
    **override,
  }
  result, _, _ = intake_workflow("decide", json.dumps(payload))
  assert result.returncode != 0


def test_invalid_json_is_a_workflow_failure(intake_workflow):
  """A command that returns malformed JSON cannot report successful validation."""
  result, _, _ = intake_workflow("decide", "not JSON")
  assert result.returncode != 0


@pytest.mark.parametrize("failed_command", ["intake", "git"])
def test_workflow_command_errors_fail_closed(intake_workflow, failed_command):
  """Actual command failures cannot be hidden by parsing or file selection."""
  result, _, _ = intake_workflow(
    "decide",
    "{}",
    command_exit=7 if failed_command == "intake" else 0,
    git_exit=7 if failed_command == "git" else 0,
  )
  assert result.returncode != 0


@pytest.mark.parametrize(
  "response", ["HTTP/2 404", "HTTP/2 403", "HTTP/2 500", "network unavailable"]
)
def test_unconfirmed_membership_remains_an_eligibility_failure(
  tmp_path, intake_workflow, response
):
  """Public-membership ambiguity and API errors never confirm eligibility."""
  result, _, calls = intake_workflow(
    "membership", membership_exit=1, membership=response
  )
  assert result.returncode != 0
  assert "::error::" in result.stdout
  assert calls == [["gh", "api", "--include", "orgs/bcgov/members/contributor"]]
  output = tmp_path / "outputs.txt"
  assert not output.exists() or "member=yes" not in output.read_text()
