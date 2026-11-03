"""Exercise repository test commands without executing contributed Python."""

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]


@pytest.fixture
def repository(tmp_path):
  """Create trusted tests beside guarded, inert contributed Python files."""
  shutil.copyfile(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
  tests = tmp_path / "tests"
  tests.mkdir()
  (tests / "test_tooling.py").write_text(
    'def test_repository_tooling():\n  """Repository tooling still runs."""\n',
    encoding="utf-8",
  )
  security = tests / "security-policy"
  security.mkdir()
  (security / "test_policy.py").write_text(
    'def test_security_fixture():\n  """Security fixtures still run."""\n',
    encoding="utf-8",
  )
  for asset_type in ("skills", "prompts", "instructions", "agents"):
    package = tmp_path / asset_type / "community" / "submitted" / "scripts"
    package.mkdir(parents=True)
    for name in ("test_contributed.py", "conftest.py"):
      (package / name).write_text(
        '"""Inert package discovery sentinel."""\n', encoding="utf-8"
      )
  # This trusted plugin refuses exec before Python can run any package module.
  (tmp_path / "execution_guard.py").write_text(
    "import pathlib, sys\n"
    "root = pathlib.Path(__file__).parent\n"
    "assets = [root / name for name in "
    "('skills', 'prompts', 'instructions', 'agents')]\n"
    "def guard(event, args):\n"
    "  if event == 'exec':\n"
    "    path = pathlib.Path(args[0].co_filename).resolve()\n"
    "    if any(path.is_relative_to(asset) for asset in assets):\n"
    "      (root / 'package-import-attempt').write_text(str(path))\n"
    "      raise RuntimeError('package execution refused by test guard')\n"
    "sys.addaudithook(guard)\n",
    encoding="utf-8",
  )
  return tmp_path, {
    **os.environ,
    "PYTHONPATH": str(tmp_path),
    "PYTEST_ADDOPTS": "-p execution_guard",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "UV_PROJECT_ENVIRONMENT": sys.prefix,
    "UV_NO_SYNC": "true",
  }


def test_default_pytest_only_executes_repository_tests(repository):
  """Default discovery keeps package tests and conftests outside execution."""
  tmp_path, env = repository
  command = [sys.executable, "-m", "pytest", "-q"]
  _check_test_command(command, tmp_path, env)


def _check_test_command(command, root, env, expected=2):
  """Observe actual collection and invocation with package execution guarded."""
  collected = subprocess.run(
    [*command, "--collect-only"], cwd=root, env=env, capture_output=True, text=True
  )
  assert collected.returncode == 0, collected.stdout + collected.stderr
  if expected == 2:
    assert "test_tooling.py::test_repository_tooling" in collected.stdout
  assert "test_policy.py::test_security_fixture" in collected.stdout
  assert "test_contributed.py" not in collected.stdout
  executed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
  assert executed.returncode == 0, executed.stdout + executed.stderr
  assert f"{expected} passed" in executed.stdout
  assert not (root / "package-import-attempt").exists()


@pytest.mark.parametrize("target", ["test", "verify"])
def test_make_test_commands_explicitly_select_repository_tests(repository, target):
  """Supported Make recipes remain safe even without default discovery rules."""
  root, env = repository
  env["PYTEST_ADDOPTS"] += " -o testpaths="
  recipe = (ROOT / "Makefile").read_text().split(f"\n{target}:\n", 1)[1]
  command = next(
    line.strip()
    for line in recipe.split("\n\n", 1)[0].splitlines()
    if "uv run pytest" in line
  )
  _check_test_command(shlex.split(command), root, env)


@pytest.mark.parametrize(
  "step_name,expected",
  [("Run unit tests", 2), ("Run Security-owned policy fixtures", 1)],
)
def test_ci_test_commands_explicitly_select_repository_tests(
  repository, step_name, expected
):
  """CI invokes repository tests and the Security fixtures as bounded inputs."""
  root, env = repository
  env["PYTEST_ADDOPTS"] += " -o testpaths="
  workflow = yaml.safe_load((ROOT / ".github/workflows/pr.yml").read_text())
  command = next(
    step["run"]
    for step in workflow["jobs"]["lint-tests"]["steps"]
    if step.get("name") == step_name
  )
  _check_test_command(shlex.split(command), root, env, expected)


def test_creator_preview_executes_only_repository_tests(
  repository, monkeypatch, capsys
):
  """The retained creator preview invokes pytest without discovering packages."""
  root, env = repository
  env["PYTEST_ADDOPTS"] += " -o testpaths="
  for key, value in env.items():
    monkeypatch.setenv(key, value)
  package = root / "skills/community/submitted"
  (package / "bcgov-extension.yaml").write_text("capabilities: {}\n")
  spec = importlib.util.spec_from_file_location(
    "creator_execution", ROOT / "scripts/create_extension.py"
  )
  creator = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(creator)
  run = subprocess.run

  def execute(command, **kwargs):
    """Run the actual pytest process; supply other repository command results."""
    if command[:3] == ["uv", "run", "pytest"]:
      return run(command, **kwargs)
    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

  monkeypatch.setattr(subprocess, "run", execute)
  status = creator.main(["preview", "--marketplace", str(root), "--name", "submitted"])
  output = capsys.readouterr()
  assert status == 0, output.err
  preview = json.loads(output.out)
  test_result = next(
    item
    for item in preview["validation"]
    if item["command"].startswith("uv run pytest ")
  )
  assert "2 passed" in test_result["output"]
  assert not (root / "package-import-attempt").exists()
