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
  assert expected in {item["code"] for item in scan["findings"]}


def test_approved_script_rule_blocks_undeclared_script(tmp_path):
  """An undeclared script is never publishable."""
  package = tmp_path / "skills" / "community" / "sample"
  (package / "scripts").mkdir(parents=True)
  (package / "SKILL.md").write_text("# Sample\n")
  (package / m.MANIFEST_NAME).write_text("id: bcgov-public/sample\n")
  (package / "scripts" / "run.sh").write_text("echo hello\n")
  scan = m.scan_package(package, {"capabilities": {}})
  assert "undeclared-script" in {item["code"] for item in scan["findings"]}


def test_benign_declared_package_passes(tmp_path):
  """An ordinary instruction remains publishable."""
  package = tmp_path / "skills" / "community" / "sample"
  package.mkdir(parents=True)
  (package / "SKILL.md").write_text("# Sample\nA safe instruction.\n")
  (package / m.MANIFEST_NAME).write_text("id: bcgov-public/sample\n")
  assert m.scan_package(package, {"capabilities": {}})["outcome"] == "passed"
