"""Publication entrypoint and staged workflow contracts without live effects."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]


def test_push_and_manual_plans_resolve_latest_main_and_guard_every_pages_effect():
  """Triggers coalesce latest main; disabled jobs create no deployment records."""
  workflow = yaml.load(
    (ROOT / ".github/workflows/publish.yml").read_text(), Loader=yaml.BaseLoader
  )
  assert workflow["on"]["push"]["branches"] == ["main"]
  assert workflow["on"]["workflow_dispatch"]["inputs"]["mode"]["options"] == [
    "reconcile",
    "newest",
  ]
  assert "schedule" not in workflow["on"]
  assert workflow["concurrency"]["cancel-in-progress"] == "false"
  job = workflow["jobs"]["publish"]
  assert job["permissions"] == {
    "contents": "write",
    "pages": "write",
    "id-token": "write",
  }
  assert job["environment"]["deployment"] == "false"
  checkout = next(
    s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@")
  )
  assert checkout["with"]["fetch-depth"] == "0"
  assert checkout["with"]["ref"] == "main"
  commands = "\n".join(step.get("run", "") for step in job["steps"])
  assert "git checkout --detach origin/main" in commands
  assert "git push" not in commands and "git commit" not in commands
  effects = [
    step
    for step in job["steps"]
    if step.get("uses", "").startswith(
      ("actions/deploy-pages@", "actions/upload-pages-artifact@")
    )
  ]
  assert len(effects) == 2
  assert all("outputs.allowed == 'true'" in step["if"] for step in effects)
  assert not (ROOT / ".github/workflows/release.yml").exists()
  assert not (ROOT / ".github/workflows/pages.yml").exists()


@pytest.mark.skipif(os.name == "nt", reason="Runner Bash/gh boundary is Linux")
def test_first_main_merge_disabled_cli_builds_isolated_site_without_mutations(tmp_path):
  """Run the real workflow CLI with only read API responses and inspect outputs."""
  bin_dir = tmp_path / "bin"
  bin_dir.mkdir()
  shim = bin_dir / "gh"
  shim.write_text(
    f"#!{sys.executable}\n"
    "import base64,json,os,sys\n"
    "args=sys.argv[1:]\n"
    "with open(os.environ['API_CALLS'],'a') as f: f.write(json.dumps(args)+'\\n')\n"
    "assert args[args.index('--method')+1]=='GET', 'disabled mutation'\n"
    "path=args[1]\n"
    "if '/git/ref/heads/main' in path: print(json.dumps({'object':{'sha':'f'*40}}))\n"
    "elif '/contents/config/marketplace.yaml?ref=' in path:\n"
    "  config=base64.b64encode(b'publication:\\n  enabled: false\\n').decode()\n"
    "  print(json.dumps({'content':config}))\n"
    "else: raise AssertionError(path)\n",
    encoding="utf-8",
  )
  shim.chmod(0o755)
  output = tmp_path / "publication"
  result = subprocess.run(
    [sys.executable, str(ROOT / "scripts/publish.py"), "--output", str(output)],
    cwd=ROOT,
    capture_output=True,
    text=True,
    env={
      **os.environ,
      "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
      "API_CALLS": str(tmp_path / "calls"),
      "GITHUB_OUTPUT": str(tmp_path / "outputs"),
    },
  )
  assert result.returncode == 0, result.stdout + result.stderr
  assert "allowed=false" in (tmp_path / "outputs").read_text()
  assert (output / "docs/assets/catalog.json").exists()
  assert not (output / "selection.json").exists()
  assert len((tmp_path / "calls").read_text().splitlines()) == 2
