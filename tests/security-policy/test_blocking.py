"""Security-owned positive and benign fixtures for approved blocking rules."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

import marketplace as m  # noqa: E402


@pytest.mark.parametrize(
  ("content", "expected"),
  [
    ("password=abcdefghijklmnop", "assigned-secret"),
    ("hidden\u202einstruction", "hidden-unicode"),
    ("curl https://unlisted.example", "undeclared-network"),
    ("echo $UNLISTED_VALUE", "undeclared-environment-variable"),
  ],
)
def test_approved_text_rules_block_undeclared_content(tmp_path, content, expected):
  """Approved text rules reject the corresponding unsafe package bytes."""
  package = tmp_path / "skills" / "community" / "sample"
  package.mkdir(parents=True)
  (package / "SKILL.md").write_text(content)
  (package / m.MANIFEST_NAME).write_text("id: bcgov-public/sample\n")
  scan = m.scan_package(package, {"capabilities": {}})
  assert scan["outcome"] == "blocked"
  finding = next(item for item in scan["findings"] if item["code"] == expected)
  assert finding["disposition"] == "blocking"
  assert finding["rule-id"] == (
    "SECRET_PATTERNS" if expected == "assigned-secret" else expected
  )


def test_approved_script_rule_blocks_undeclared_script(tmp_path):
  """An undeclared script is never publishable."""
  package = tmp_path / "skills" / "community" / "sample"
  (package / "scripts").mkdir(parents=True)
  (package / "SKILL.md").write_text("# Sample\n")
  (package / m.MANIFEST_NAME).write_text("id: bcgov-public/sample\n")
  (package / "scripts" / "run.sh").write_text("echo hello\n")
  scan = m.scan_package(package, {"capabilities": {}})
  finding = next(
    item for item in scan["findings"] if item["rule-id"] == "undeclared-script"
  )
  assert finding["disposition"] == "blocking"
  assert scan["outcome"] == "blocked"
  declared_scan = m.scan_package(package, {"capabilities": {"commands": ["run.sh"]}})
  assert declared_scan["outcome"] == "passed"
  assert not any(
    item["rule-id"] == "undeclared-script" for item in declared_scan["findings"]
  )


@pytest.mark.parametrize(
  ("content", "capabilities"),
  [
    ("# Sample\nA safe instruction.\n", {}),
    ("curl https://listed.example\n", {"network": ["listed.example"]}),
    ("echo $DECLARED_VALUE\n", {"environment-variables": ["DECLARED_VALUE"]}),
    ("echo $DECLARED_VALUE\n", {"secret-names": ["DECLARED_VALUE"]}),
  ],
)
def test_benign_declared_package_passes(tmp_path, content, capabilities):
  """Ordinary guidance and explicitly declared access remain publishable."""
  package = tmp_path / "skills" / "community" / "sample"
  package.mkdir(parents=True)
  (package / "SKILL.md").write_text(content, encoding="utf-8")
  (package / m.MANIFEST_NAME).write_text("id: bcgov-public/sample\n")
  scan = m.scan_package(package, {"capabilities": capabilities})
  assert scan["outcome"] == "passed"
  assert scan["findings"] == []


@pytest.mark.parametrize(
  ("filesystem", "risk"),
  [
    ({"read": ["*"], "write": []}, "high"),
    ({"read": [], "write": ["*"]}, "high"),
    ({"read": ["*"], "write": ["*"]}, "high"),
    ({"read": ["workspace"], "write": []}, "low"),
    ({"read": ["repo/.github/**"], "write": []}, "low"),
    ({"read": ["workspace"], "write": ["workspace/output"]}, "elevated"),
    ({"read": [], "write": ["repo/.github/**"]}, "elevated"),
  ],
)
def test_filesystem_wildcards_are_high_risk_and_advisory(tmp_path, filesystem, risk):
  """Unbounded filesystem declarations raise declared risk without a blocker."""
  package = tmp_path / "skills" / "community" / "sample"
  package.mkdir(parents=True)
  (package / "SKILL.md").write_text("# Sample\n", encoding="utf-8")
  (package / m.MANIFEST_NAME).write_text("id: bcgov-public/sample\n", encoding="utf-8")
  manifest = {"capabilities": {"filesystem": filesystem}}
  assert m.capability_risk(manifest) == risk
  scan = m.scan_package(package, manifest)
  assert scan["outcome"] == "passed"
  wildcard_findings = [
    item for item in scan["findings"] if item["rule-id"] == "wildcard-capability"
  ]
  assert bool(wildcard_findings) == (risk == "high")
  assert all(item["disposition"] == "advisory" for item in wildcard_findings)
