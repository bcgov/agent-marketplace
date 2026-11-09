"""Privileged gate workflow wiring and dormant controls without live effects."""

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_privileged_gate_uses_only_main_code_and_one_repository_wide_queue():
  """Every completion/manual retry reaches API analysis without checking out PR data."""
  workflow = yaml.load(
    (ROOT / ".github/workflows/merge-gate.yml").read_text(), Loader=yaml.BaseLoader
  )
  assert workflow["on"]["workflow_run"] == {"workflows": ["PR"], "types": ["completed"]}
  assert set(workflow["on"]["workflow_dispatch"]["inputs"]) == {"run-id", "attempt"}
  assert workflow["permissions"] == {}
  assert workflow["concurrency"] == {
    "group": "marketplace-merge-gate",
    "cancel-in-progress": "false",
    "queue": "max",
  }
  job = workflow["jobs"]["gate"]
  assert job["permissions"] == {
    "contents": "write",
    "pull-requests": "write",
    "checks": "write",
    "actions": "write",
  }
  steps = job["steps"]
  checkout = next(
    step for step in steps if step.get("uses", "").startswith("actions/checkout@")
  )
  assert checkout["with"] == {"ref": "main", "persist-credentials": "false"}
  runtime = next(
    step for step in steps if step.get("uses", "").startswith("astral-sh/setup-uv@")
  )
  assert runtime["with"]["enable-cache"] == "false"
  commands = "\n".join(step.get("run", "") for step in steps)
  assert "git checkout --detach origin/main" in commands
  assert "uv run --frozen --no-dev python scripts/gate_github.py" in commands
  assert "pull_request.head" not in commands
  assert "download-artifact" not in str(steps)
  assert "actions/cache" not in str(steps)
  assert "gh pr merge" not in commands
  assert "--auto" not in commands
  assert "ORG_READ_TOKEN" not in str(steps)


def test_all_operational_switches_are_off_and_legacy_auto_paths_are_absent():
  """Merging implementation cannot activate publication or either automatic route."""
  config = yaml.safe_load((ROOT / "config/marketplace.yaml").read_text())
  assert config["publication"]["enabled"] is False
  assert config["community-intake"]["auto-publish"] is False
  assert config["dependency-intake"]["auto-merge"] is False
  assert not (ROOT / ".github/workflows/community-intake.yml").exists()
  assert not (ROOT / ".github/workflows/dependabot-auto-merge.yml").exists()
