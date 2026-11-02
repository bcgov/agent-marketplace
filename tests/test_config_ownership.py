"""Registry and security policy contracts at the marketplace CLI boundary."""

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
CLI = ROOT / "scripts" / "marketplace.py"


def test_committed_codeowners_matches_registry():
  """The checked-in projection matches validated registry ownership."""
  result = subprocess.run(
    [sys.executable, str(CLI), "--root", str(ROOT), "validate"],
    capture_output=True,
    text=True,
  )
  assert result.returncode == 0, result.stderr
  owners = (ROOT / ".github" / "CODEOWNERS").read_text()
  assert "* @bcgov/agent-marketplace-admins" in owners
  assert "/skills/security/ @bcgov/security" in owners
  assert "/config/security-policy.yaml @bcgov/security" in owners
  assert "/tests/security-policy/ @bcgov/security" in owners
  assert "/hooks/" not in owners
  assert "/mcp/" not in owners


def test_security_approvals_remain_blocking():
  """The approved blocking set from the existing security baseline stays intact."""
  policy = yaml.safe_load((ROOT / "config" / "security-policy.yaml").read_text())
  assert policy["blocking"] == [
    "SECRET_PATTERNS",
    "hidden-unicode",
    "undeclared-network",
    "undeclared-environment-variable",
    "undeclared-script",
  ]
