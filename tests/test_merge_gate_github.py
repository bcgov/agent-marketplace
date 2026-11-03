"""End-to-end gate behavior against the GitHub HTTP request boundary."""

import base64
import copy
import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from gate_github import GitHubApi, GitHubGate

ROOT = Path(__file__).parents[1]
BASE, HEAD, MERGE = (letter * 40 for letter in "abc")
REPO = {"id": 1348843536, "full_name": "bcgov/agent-marketplace"}


def object_sha(data):
  """Use Git's independently specified blob object format."""
  return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class GitHub:
  """Model authoritative GitHub resources and effects without executing PR data."""

  def __init__(self):
    """Start with exact successful PR jobs and one new benign Community package."""
    self.blobs = {}
    self.base = {}
    for directory in ("config", "schemas"):
      for path in (ROOT / directory).iterdir():
        if path.is_file():
          self.base[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for name in (
      ".github/workflows/pr.yml",
      ".github/dependabot.yml",
      "pyproject.toml",
      "uv.lock",
    ):
      self.base[name] = (ROOT / name).read_bytes()
    config = yaml.safe_load(self.base["config/marketplace.yaml"])
    config["publication"]["enabled"] = True
    config["community-intake"]["auto-publish"] = True
    config["dependency-intake"] = {"auto-merge": False}
    self.base["config/marketplace.yaml"] = yaml.safe_dump(config).encode()
    self.head = dict(self.base)
    for path in (ROOT / "tests/fixtures/submissions/benign-submission").rglob("*"):
      if path.is_file():
        self.head[
          "skills/community/demo/"
          + path.relative_to(
            ROOT / "tests/fixtures/submissions/benign-submission"
          ).as_posix()
        ] = path.read_bytes()
    self.pr = {
      "number": 71,
      "state": "open",
      "draft": False,
      "user": {"login": "Alice", "id": 1, "type": "User"},
      "head": {"sha": HEAD, "ref": "demo", "repo": {"id": 2}},
      "base": {"sha": BASE, "ref": "main", "repo": REPO},
      "merge_commit_sha": MERGE,
    }
    self.run = {
      "id": 99,
      "run_attempt": 1,
      "repository": REPO,
      "head_repository": {"id": 2},
      "workflow_id": 365544835,
      "path": ".github/workflows/pr.yml",
      "event": "pull_request",
      "head_sha": HEAD,
      "status": "completed",
      "conclusion": "success",
      "pull_requests": [
        {
          "number": 71,
          "head": copy.deepcopy(self.pr["head"]),
          "base": copy.deepcopy(self.pr["base"]),
        }
      ],
    }
    self.jobs = [
      {
        "id": i,
        "name": name,
        "run_id": 99,
        "head_sha": HEAD,
        "status": "completed",
        "conclusion": "success",
      }
      for i, name in enumerate(
        ("fork-gate", "lint-tests", "skills", "marketplace", "results"), 1
      )
    ]
    self.membership = 204
    self.checks, self.comments, self.effects, self.reads = [], [], [], []
    self.history = []
    self.current_base = BASE
    self.truncated = False
    self.omit_inventory = False
    self.dispatch_fails = False
    self.before_merge = None
    self.before_recheck = None
    self.pr_reads = 0
    self.extra_changes = []
    self.modes = {}
    self.revisions = {}
    self.commits = {}
    self.prs = {}
    self.comparison_heads = None

  def tree(self, files):
    """Expose complete Git trees with independently hashed immutable blobs."""
    entries = []
    for path, content in sorted(files.items()):
      sha = object_sha(content)
      self.blobs[sha] = content
      entries.append(
        {
          "path": path,
          "sha": sha,
          "size": len(content),
          "mode": self.modes.get(path, "100644"),
          "type": "blob",
        }
      )
    return {"truncated": self.truncated, "tree": entries}

  def changes(self):
    """Compute provider file metadata, including resource-only changes and deletions."""
    changed = []
    for path in sorted(self.base.keys() | self.head.keys()):
      if self.base.get(path) != self.head.get(path):
        changed.append(
          {
            "filename": path,
            "status": "removed"
            if path not in self.head
            else "added"
            if path not in self.base
            else "modified",
          }
        )
    return changed + self.extra_changes

  def request(self, method, path, data=None):
    """Supply public API facts and record only external mutation requests."""
    prefix = "repos/bcgov/agent-marketplace/"
    endpoint = path.removeprefix(prefix)
    if method != "GET":
      self.effects.append((method, endpoint, copy.deepcopy(data)))
      if endpoint == "check-runs":
        check = {**data, "id": len(self.checks) + 1, "app": {"slug": "github-actions"}}
        self.checks.append(check)
        return check
      if endpoint.startswith("check-runs/"):
        self.checks[int(endpoint.split("/")[-1]) - 1].update(data)
        return {}
      if endpoint == "issues/71/comments":
        self.comments.append(
          {
            **data,
            "id": len(self.comments) + 1,
            "user": {"login": "github-actions[bot]"},
          }
        )
        return self.comments[-1]
      if endpoint.startswith("issues/comments/"):
        self.comments[int(endpoint.split("/")[-1]) - 1].update(data)
        return {}
      if endpoint == "pulls/71/merge":
        if self.before_merge:
          self.before_merge(self)
        if data["sha"] != self.pr["head"]["sha"]:
          raise RuntimeError("409 expected head mismatch")
        self.pr["state"] = "closed"
        self.pr["merged"] = True
        return {"merged": True, "sha": "d" * 40}
      if endpoint == "actions/workflows/publish.yml/dispatches":
        if self.dispatch_fails:
          raise RuntimeError("503 dispatch unavailable")
        return {
          "workflow_run_id": 88,
          "html_url": "https://github.com/bcgov/agent-marketplace/actions/runs/88",
        }
      raise AssertionError((method, endpoint, data))
    self.reads.append(endpoint)
    route, _, query = endpoint.partition("?")
    page = int(
      dict(item.split("=") for item in query.split("&") if "=" in item).get("page", 1)
    )
    if route == "actions/runs/99" or route == "actions/runs/99/attempts/1":
      return copy.deepcopy(self.run)
    if route == "actions/workflows/365544835":
      return {"id": 365544835, "path": ".github/workflows/pr.yml", "state": "active"}
    if route == "pulls/71":
      self.pr_reads += 1
      if self.pr_reads == 2 and self.before_recheck:
        self.before_recheck(self)
      return {**copy.deepcopy(self.pr), "changed_files": len(self.changes())}
    if route in self.prs:
      return copy.deepcopy(self.prs[route])
    if route == "git/ref/heads/main":
      return {"object": {"sha": self.current_base}}
    if route == "actions/runs/99/attempts/1/jobs":
      return {
        "total_count": len(self.jobs),
        "jobs": self.jobs[(page - 1) * 100 : page * 100],
      }
    if route == "pulls/71/files":
      return self.changes()[(page - 1) * 100 : page * 100]
    if route == f"git/trees/{BASE}":
      return self.tree(self.base)
    if route == f"git/trees/{HEAD}":
      return self.tree(self.head)
    if route.startswith("git/trees/") and route.split("/")[-1] in self.revisions:
      return self.tree(self.revisions[route.split("/")[-1]])
    if route.startswith("git/blobs/"):
      content = self.blobs[route.split("/")[-1]]
      return {
        "encoding": "base64",
        "size": len(content),
        "content": base64.b64encode(content).decode(),
      }
    if route == f"git/commits/{MERGE}":
      return {
        "sha": MERGE,
        "parents": [
          {"sha": value} for value in (self.comparison_heads or [BASE, HEAD])
        ],
      }
    if route in self.commits:
      return copy.deepcopy(self.commits[route])
    if route == "pulls":
      return self.history[(page - 1) * 100 : page * 100]
    if route == f"commits/{HEAD}/check-runs":
      return {"total_count": len(self.checks), "check_runs": copy.deepcopy(self.checks)}
    if route == "issues/71/comments":
      return copy.deepcopy(self.comments)
    if route == f"commits/{HEAD}/pulls":
      return [copy.deepcopy(self.pr)]
    raise AssertionError((method, endpoint))

  def public_membership(self, author):
    """Return the HTTP result, never inferred private organization membership."""
    return self.membership


def gate(api):
  """Construct the production adapter with a pinned trusted-main source revision."""
  return GitHubGate(
    ROOT, api=api, trusted_sha=BASE, now=datetime(2026, 11, 3, 23, tzinfo=UTC)
  )


def test_exact_head_check_guarded_merge_dispatch_and_repeat_delivery():
  """A fully trusted eligible change gets an explicit head check and one merge."""
  api = GitHub()
  result = gate(api).run(99, 1)
  assert result["route"] == "community-auto"
  assert api.checks[0]["head_sha"] == HEAD
  assert api.checks[0]["name"] == "merge-gate"
  assert api.checks[0]["output"]["title"] == "community-auto"
  merge = next(
    data for _, endpoint, data in api.effects if endpoint == "pulls/71/merge"
  )
  assert merge == {"sha": HEAD, "merge_method": "squash"}
  assert any(
    endpoint == "actions/workflows/publish.yml/dispatches"
    for _, endpoint, _ in api.effects
  )
  effects = copy.deepcopy(api.effects)
  gate(api).run(99, 1)
  assert api.effects == effects


def configure(api, section, key, value):
  """Change an immutable fixture's trusted policy before the run is observed."""
  config = yaml.safe_load(api.base["config/marketplace.yaml"])
  config[section][key] = value
  api.base["config/marketplace.yaml"] = yaml.safe_dump(config).encode()
  api.head["config/marketplace.yaml"] = api.base["config/marketplace.yaml"]


@pytest.mark.parametrize(
  "field,value",
  [
    ("repository", {"id": 12, "full_name": REPO["full_name"]}),
    ("workflow_id", 22),
    ("path", ".github/workflows/impostor.yml"),
    ("event", "push"),
    ("id", 100),
    ("run_attempt", 2),
  ],
)
def test_wrong_provider_origin_never_writes_a_routing_check(field, value):
  """A PR label, workflow name or claimed JSON result cannot authenticate origin."""
  api = GitHub()
  api.run[field] = value
  result = gate(api).run(99, 1)
  assert result["write"] is False
  assert api.effects == []


@pytest.mark.parametrize(
  "missing", ["fork-gate", "lint-tests", "skills", "marketplace", "results"]
)
def test_same_named_check_from_another_workflow_does_not_supply_required_job(missing):
  """Only jobs of the authenticated numeric workflow attempt count as prerequisites."""
  api = GitHub()
  api.jobs = [job for job in api.jobs if job["name"] != missing]
  api.checks = [
    {
      "name": missing,
      "conclusion": "success",
      "id": 999,
      "app": {"slug": "github-actions"},
    }
  ]
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert result["conclusion"] == "success"
  assert "Required jobs" in " ".join(result["reasons"])
  assert not any(endpoint.endswith("/merge") for _, endpoint, _ in api.effects)


@pytest.mark.parametrize("member", [404, 403, 429, "network error"])
def test_public_membership_unknown_is_a_successful_review_hold(member):
  """HTTP failures cannot establish outsider status or broaden contributor policy."""
  api = GitHub()
  api.membership = member
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert result["conclusion"] == "success"
  assert str(member) in " ".join(result["reasons"])
  assert len(api.checks) == 1
  assert not any(endpoint.endswith("/merge") for _, endpoint, _ in api.effects)


def test_stale_head_completion_does_not_write_against_new_revision():
  """Older run delivery cannot update diagnostics for a newer head."""
  api = GitHub()
  api.pr["head"]["sha"] = "f" * 40
  gate(api).run(99, 1)
  assert api.effects == []


@pytest.mark.parametrize(
  "kind", ["tested-base", "merge-parents", "missing-fork-association", "draft"]
)
def test_unavailable_exact_tested_base_is_a_current_head_review_hold(kind):
  """Historical association plus default checkout maps the tested merge explicitly."""
  api = GitHub()
  if kind == "tested-base":
    api.run["pull_requests"][0]["base"]["sha"] = "e" * 40
  elif kind == "merge-parents":
    api.comparison_heads = ["e" * 40, HEAD]
  elif kind == "missing-fork-association":
    api.run["pull_requests"] = []
  else:
    api.pr["draft"] = True
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert api.checks[0]["head_sha"] == HEAD
  assert not any(endpoint.endswith("/merge") for _, endpoint, _ in api.effects)


def test_disabled_publication_holds_and_real_block_still_fails():
  """Shared publication readiness never suppresses trusted package validation."""
  api = GitHub()
  configure(api, "publication", "enabled", False)
  assert gate(api).run(99, 1)["route"] == "human-review"
  assert not any(
    endpoint.endswith(("/merge", "/dispatches")) for _, endpoint, _ in api.effects
  )
  api.head["skills/community/demo/SKILL.md"] += b"\ncurl https://undeclared.example\n"
  result = gate(api).run(99, 1)
  assert result["conclusion"] == "failure"
  assert "undeclared-network" in " ".join(result["reasons"])


def existing(api):
  """Give the trusted base a genuine active package maintained by Alice."""
  for path in api.head.keys() - api.base.keys():
    api.base[path] = api.head[path]
  path = "skills/community/demo/bcgov-extension.yaml"
  manifest = yaml.safe_load(api.base[path])
  manifest["maintainers"] = ["@ALICE"]
  api.base[path] = api.head[path] = yaml.safe_dump(manifest).encode()


def test_manifest_only_edit_scans_unchanged_resources_and_binds_one_complete_digest():
  """Removing a declaration fails for an unchanged resource outside the patch."""
  api = GitHub()
  existing(api)
  resource = "skills/community/demo/references/guide.md"
  api.base[resource] = api.head[resource] = b"curl https://declared.example\n"
  path = "skills/community/demo/bcgov-extension.yaml"
  manifest = yaml.safe_load(api.base[path])
  manifest["capabilities"]["network"] = ["declared.example"]
  api.base[path] = yaml.safe_dump(manifest).encode()
  result = gate(api).run(99, 1)
  assert result["conclusion"] == "failure"
  assert "undeclared-network" in " ".join(result["reasons"])
  assert "3 complete files" in api.comments[-1]["body"]
  assert "sha256:" in api.comments[-1]["body"]


def test_resource_only_edit_is_scanned_and_mentions_only_base_contacts():
  """A content edit needs no Manifest diff to reach trusted analysis and contacts."""
  api = GitHub()
  existing(api)
  api.head["skills/community/demo/references/guide.md"] = (
    b"curl https://unlisted.example\n"
  )
  result = gate(api).run(99, 1)
  assert result["conclusion"] == "failure"
  assert "@ALICE" in api.comments[-1]["body"]


@pytest.mark.parametrize("mode", ["100755", "120000", "160000"])
def test_executable_symlink_and_gitlink_package_entries_are_hard_failures(mode):
  """Modes are enforced from Git objects instead of the temporary filesystem."""
  api = GitHub()
  api.modes["skills/community/demo/SKILL.md"] = mode
  configure(api, "community-intake", "auto-publish", False)
  assert gate(api).run(99, 1)["conclusion"] == "failure"


def test_truncated_inventory_holds_without_trusting_pr_success():
  """A successful PR run cannot replace a complete resulting package inventory."""
  api = GitHub()
  api.truncated = True
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert "truncated" in " ".join(result["reasons"])


def test_proposed_validator_and_policy_cannot_manufacture_eligibility():
  """Trusted-base scan finds blocks even if proposed scanner/policy claims success."""
  api = GitHub()
  api.head["scripts/marketplace.py"] = b"raise RuntimeError('must never execute')\n"
  policy = yaml.safe_load(api.head["config/security-policy.yaml"])
  policy["blocking"] = []
  api.head["config/security-policy.yaml"] = yaml.safe_dump(policy).encode()
  api.head["skills/community/demo/SKILL.md"] += b"\ncurl https://unlisted.example\n"
  assert gate(api).run(99, 1)["conclusion"] == "failure"


def test_final_revalidation_detects_concurrent_head_change_before_any_effect():
  """Revalidation cannot let an earlier success authorize a later revision."""
  api = GitHub()
  api.before_recheck = lambda remote: remote.pr["head"].update(sha="e" * 40)
  result = gate(api).run(99, 1)
  assert result["write"] is False
  assert api.effects == []


def test_expected_head_guard_handles_a_race_after_final_read_without_dispatch():
  """The merge API's SHA parameter closes the final head race."""
  api = GitHub()
  api.before_merge = lambda remote: remote.pr["head"].update(sha="e" * 40)
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert not any(endpoint.endswith("/dispatches") for _, endpoint, _ in api.effects)


def test_failed_publication_dispatch_diagnoses_manual_recovery_on_merged_pr():
  """A confirmed merge is not undone or falsely reported as published."""
  api = GitHub()
  api.dispatch_fails = True
  result = gate(api).run(99, 1)
  assert api.pr["merged"] is True
  assert "Manually run publish.yml" in " ".join(result["reasons"])
  assert "publish dispatch failed" in api.comments[-1]["body"]


def test_valid_hold_delivery_reuses_its_check_and_comment():
  """Repeated delivery updates one stable head diagnostic without duplicating it."""
  api = GitHub()
  api.membership = 404
  gate(api).run(99, 1)
  effects = copy.deepcopy(api.effects)
  gate(api).run(99, 1)
  assert len(api.checks) == len(api.comments) == 1
  assert api.effects == effects


@pytest.mark.parametrize(
  "key,value",
  [
    ("window-days", 0),
    ("window-days", 6),
    ("max-new-packages-per-window", 11),
    ("auto-publish-risk-ceiling", "high"),
  ],
)
def test_trusted_policy_cannot_broaden_the_locked_community_limits(key, value):
  """Operational policy cannot silently authorize more than the locked contract."""
  api = GitHub()
  configure(api, "community-intake", key, value)
  result = gate(api).run(99, 1)
  assert result["conclusion"] == "failure"
  assert not any(endpoint.endswith("/merge") for _, endpoint, _ in api.effects)


def dependabot(api, ecosystem="github_actions"):
  """Use authoritative bot user/commit metadata with a genuine signed group block."""
  api.head = dict(api.base)
  actor = {"id": 49699333, "login": "dependabot[bot]", "type": "Bot"}
  api.pr["user"] = actor
  group = "github-actions" if ecosystem == "github_actions" else "python"
  api.pr["head"]["repo"] = dict(REPO)
  api.run["head_repository"] = dict(REPO)
  api.pr["head"]["ref"] = f"dependabot/{ecosystem}/{group}-0123abcd"
  api.run["pull_requests"][0]["head"] = copy.deepcopy(api.pr["head"])
  dependency = "astral-sh/setup-uv" if ecosystem == "github_actions" else "jsonschema"
  api.commits[f"commits/{HEAD}"] = {
    "sha": HEAD,
    "author": actor,
    "commit": {
      "verification": {"verified": True},
      "message": f"Bump the {group} group with a major update\n\n"
      "---\nupdated-dependencies:\n"
      f"- dependency-name: {dependency}\n  update-type: version-update:semver-major\n"
      f"dependency-group: {group}\n...\n",
    },
  }
  if ecosystem == "github_actions":
    path = ".github/workflows/pr.yml"
    api.head[path] = api.base[path].replace(
      b"20cfd1bf945f4377ade1205e4dbc17946fc9a30d", b"f" * 40
    )
  else:
    api.head["pyproject.toml"] = api.base["pyproject.toml"].replace(
      b"jsonschema>=4.25.1", b"jsonschema>=5.0.0"
    )
  configure(api, "dependency-intake", "auto-merge", True)


@pytest.mark.parametrize("ecosystem", ["github_actions", "uv"])
def test_genuine_grouped_dependabot_major_updates_have_independent_route(ecosystem):
  """Signed head metadata and trusted groups independently authorize major bumps."""
  api = GitHub()
  dependabot(api, ecosystem)
  configure(api, "community-intake", "auto-publish", False)
  api.membership = 404
  result = gate(api).run(99, 1)
  assert result["route"] == "dependency-auto"
  assert any(endpoint.endswith("/merge") for _, endpoint, _ in api.effects)


@pytest.mark.parametrize(
  "mutation",
  [
    "permission",
    "trigger",
    "command",
    "owner",
    "duplicate-key",
    "alias",
    "forged-creator",
    "unverified-head",
    "wrong-group",
    "ungrouped",
    "other-ecosystem",
    "tooling",
    "uv-tool-config",
  ],
)
def test_dependabot_scope_and_metadata_cannot_be_spoofed(mutation):
  """Version bumps cannot hide altered workflow authority or tooling."""
  api = GitHub()
  dependabot(api)
  path = ".github/workflows/pr.yml"
  if mutation == "permission":
    api.head[path] = api.head[path].replace(b"contents: read", b"contents: write")
  elif mutation == "trigger":
    api.head[path] = api.head[path].replace(
      b"  pull_request:", b"  pull_request_target:"
    )
  elif mutation == "command":
    api.head[path] += b"\n      - run: echo compromised\n"
  elif mutation == "owner":
    api.head[path] = api.head[path].replace(
      b"astral-sh/setup-uv@", b"attacker/setup-uv@"
    )
  elif mutation == "duplicate-key":
    api.head[path] += b"\npermissions:\n  contents: write\n"
  elif mutation == "alias":
    api.head[path] += b"\nx-extra: &permission {contents: write}\nx-copy: *permission\n"
  elif mutation == "forged-creator":
    api.pr["user"] = {"id": 999, "login": "dependabot[bot]", "type": "Bot"}
  elif mutation == "unverified-head":
    api.commits[f"commits/{HEAD}"]["commit"]["verification"]["verified"] = False
  elif mutation == "wrong-group":
    api.commits[f"commits/{HEAD}"]["commit"]["message"] = api.commits[
      f"commits/{HEAD}"
    ]["commit"]["message"].replace(
      "dependency-group: github-actions", "dependency-group: invented"
    )
  elif mutation == "ungrouped":
    api.commits[f"commits/{HEAD}"]["commit"]["message"] = (
      "Bump uv\n---\nupdated-dependencies:\n"
      "- dependency-name: astral-sh/setup-uv\n...\n"
    )
  elif mutation == "other-ecosystem":
    api.pr["head"]["ref"] = "dependabot/npm_and_yarn/github-actions"
  elif mutation == "tooling":
    api.head["scripts/gate_github.py"] = b"raise Exception('inert')\n"
  else:
    dependabot(api, "uv")
    api.head["pyproject.toml"] += b"\n[tool.malicious]\ncommand = 'execute'\n"
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert not any(endpoint.endswith("/merge") for _, endpoint, _ in api.effects)


def test_dependency_route_stays_dormant_without_publication_and_own_enable():
  """Shared and separate switches each independently stop dependency mutation."""
  for section, key in (("publication", "enabled"), ("dependency-intake", "auto-merge")):
    api = GitHub()
    dependabot(api)
    configure(api, section, key, False)
    assert gate(api).run(99, 1)["route"] == "human-review"
    assert not any(
      endpoint.endswith(("/merge", "/dispatches")) for _, endpoint, _ in api.effects
    )


def ledger(api, count, *, when="2026-11-03T20:22:02Z", author="Alice"):
  """One squash merged PR introduces a batch; its historical PR base is irrelevant."""
  before, after = "e" * 40, "f" * 40
  api.revisions[before] = dict(api.base)
  api.revisions[after] = dict(api.base)
  for index in range(count):
    api.revisions[after][f"skills/community/history-{index}/bcgov-extension.yaml"] = (
      b"maintainers: [Alice]\ncapabilities: none\n"
    )
  pr = {
    "number": 70,
    "merged": True,
    "merged_at": when,
    "merge_commit_sha": after,
    "user": {"login": author},
    "base": {"sha": "1" * 40, "ref": "main", "repo": dict(REPO)},
    "commits": 2,
  }
  api.history = [pr]
  api.prs["pulls/70"] = pr
  api.commits[f"git/commits/{after}"] = {"sha": after, "parents": [{"sha": before}]}


def test_rolling_quota_uses_merged_author_time_and_actual_squash_parent_inventories():
  """Nine historical identities plus one candidate spends exactly the final slot."""
  api = GitHub()
  ledger(api, 9)
  assert gate(api).run(99, 1)["route"] == "community-auto"
  assert f"git/trees/{'e' * 40}?recursive=1" in api.reads
  assert not any("search" in path for path in api.reads)
  api = GitHub()
  ledger(api, 10)
  assert gate(api).run(99, 1)["route"] == "human-review"


@pytest.mark.parametrize(
  "when,author", [("2026-10-20T20:22:02Z", "Alice"), ("2026-11-03T20:22:02Z", "Bob")]
)
def test_old_merges_and_other_authors_do_not_consume_candidate_budget(when, author):
  """The ledger is attributed to merge time and PR author, never commit author."""
  api = GitHub()
  ledger(api, 10, when=when, author=author)
  assert gate(api).run(99, 1)["route"] == "community-auto"


def test_competing_pr_completion_rechecks_budget_inside_the_shared_serialized_run():
  """A second candidate at nine cannot spend a slot already used by another merge."""
  api = GitHub()
  ledger(api, 9)
  api.before_recheck = lambda remote: ledger(remote, 10)
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert not any(endpoint.endswith("/merge") for _, endpoint, _ in api.effects)


def test_eleven_identity_candidate_batch_is_held_without_historical_usage():
  """A single PR cannot bypass the ceiling by introducing several manifests."""
  api = GitHub()
  native = api.head["skills/community/demo/SKILL.md"]
  manifest = api.head["skills/community/demo/bcgov-extension.yaml"]
  for index in range(10):
    api.head[f"skills/community/new-{index}/SKILL.md"] = native
    api.head[f"skills/community/new-{index}/bcgov-extension.yaml"] = manifest
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert "budget" in " ".join(result["reasons"])


@pytest.mark.parametrize(
  "kind",
  [
    "lifecycle",
    "notice",
    "redirect",
    "non-active-content",
    "restoration",
    "recreation",
    "transfer",
    "name-replacement",
    "type-replacement",
    "mixed-specialty",
  ],
)
def test_sensitive_transitions_always_require_review(kind):
  """Every lifecycle/identity/ownership exception compares trusted base records."""
  api = GitHub()
  existing(api)
  path = "skills/community/demo/bcgov-extension.yaml"
  manifest = yaml.safe_load(api.head[path])
  api.head["skills/community/demo/SKILL.md"] += b"\nClarify usage.\n"
  if kind in {"lifecycle", "notice", "non-active-content", "restoration", "recreation"}:
    if kind in {"notice", "non-active-content", "restoration", "recreation"}:
      old = {
        **manifest,
        "lifecycle": "removed" if kind == "recreation" else "quarantined",
        "notice": "Pending review.",
      }
      api.base[path] = yaml.safe_dump(old).encode()
      if kind == "recreation":
        del api.base["skills/community/demo/SKILL.md"]
    if kind in {"lifecycle", "notice", "non-active-content"}:
      manifest.update(
        lifecycle="quarantined",
        notice="Changed notice." if kind == "notice" else "Pending review.",
      )
    api.head[path] = yaml.safe_dump(manifest).encode()
  elif kind in {"transfer", "mixed-specialty"}:
    for source in list(api.head):
      if source.startswith("skills/community/demo/"):
        api.head[source.replace("/community/", "/security/")] = api.head[source]
        if kind == "transfer":
          del api.head[source]
    if kind == "mixed-specialty":
      for source in list(api.head):
        if source.startswith("skills/security/demo/"):
          api.head[source.replace("/demo/", "/second/")] = api.head.pop(source)
  else:
    target = (
      "bcgov-public/skill/second"
      if kind != "type-replacement"
      else "bcgov-public/prompt/second"
    )
    manifest.update(
      lifecycle="removed",
      notice="Use the replacement after review.",
      **{"moved-to": target},
    )
    api.head[path] = yaml.safe_dump(manifest).encode()
    del api.head["skills/community/demo/SKILL.md"]
    new_path = (
      "skills/community/second"
      if kind != "type-replacement"
      else "prompts/community/second"
    )
    api.head[new_path + "/bcgov-extension.yaml"] = api.base[path]
    api.head[
      new_path + ("/SKILL.md" if kind != "type-replacement" else "/second.prompt.md")
    ] = api.base["skills/community/demo/SKILL.md"]
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert result["conclusion"] == "success", result
  assert not any(endpoint.endswith("/merge") for _, endpoint, _ in api.effects)


def test_manifest_deletion_cannot_erase_a_trusted_unpublished_reservation():
  """Current base, rather than the last published catalogue, reserves every identity."""
  api = GitHub()
  existing(api)
  for path in list(api.head):
    if path.startswith("skills/community/demo/"):
      del api.head[path]
  assert gate(api).run(99, 1)["conclusion"] == "failure"


def test_deletion_of_native_file_is_a_hard_failure_even_when_flags_are_off():
  """The resulting package includes deletions instead of scanning only added bytes."""
  api = GitHub()
  existing(api)
  configure(api, "community-intake", "auto-publish", False)
  del api.head["skills/community/demo/SKILL.md"]
  assert gate(api).run(99, 1)["conclusion"] == "failure"


def test_all_changed_file_pages_are_analyzed_without_manifest_only_selection():
  """Resource-only changes on a second page reach complete resulting inventories."""
  api = GitHub()
  native = api.head["skills/community/demo/SKILL.md"]
  manifest = api.head["skills/community/demo/bcgov-extension.yaml"]
  api.head["skills/community/second/SKILL.md"] = native
  api.head["skills/community/second/bcgov-extension.yaml"] = manifest
  for name in ("demo", "second"):
    for index in range(51):
      api.head[f"skills/community/{name}/references/guide-{index}.md"] = (
        b"Benign resource.\n"
      )
  assert gate(api).run(99, 1)["route"] == "community-auto"
  assert any("pulls/71/files?per_page=100&page=2" == path for path in api.reads)
  assert "53 complete files" in api.comments[-1]["body"]


def test_all_closed_pr_pages_are_counted_for_author_budget():
  """An author's merged PR on page two cannot be skipped by a search shortcut."""
  api = GitHub()
  ledger(api, 10)
  api.history = [
    {"number": index, "user": {"login": "Bob"}, "merged_at": None}
    for index in range(100)
  ] + api.history
  assert gate(api).run(99, 1)["route"] == "human-review"
  assert any("state=closed" in path and "page=2" in path for path in api.reads)


def test_new_package_root_cannot_be_a_gitlink():
  """A submodule occupying a package directory cannot evade package inventory rules."""
  api = GitHub()
  api.head["skills/community/gitlink"] = b"opaque"
  api.modes["skills/community/gitlink"] = "160000"
  assert gate(api).run(99, 1)["conclusion"] == "failure"


@pytest.mark.parametrize("status", [200, 204])
def test_real_transport_preserves_public_membership_http_status(monkeypatch, status):
  """An empty HTTP 200 response is not the required public-membership 204."""

  class Response:
    """Represent an external HTTP response, not gate implementation collaborators."""

    def __enter__(self):
      """Return response headers/status when the transport opens it."""
      self.status = status
      return self

    def __exit__(self, *_args):
      """Close the simulated network response."""

    def read(self, _limit):
      """Return the provider's empty body."""
      return b""

  monkeypatch.setenv("GH_TOKEN", "test-job-token")
  monkeypatch.setattr("gate_github.urlopen", lambda *_args, **_kwargs: Response())
  assert GitHubApi().public_membership("Alice") == status


@pytest.mark.parametrize("missing", ["merged_at", "user"])
def test_incomplete_merged_author_history_cannot_silently_undercount_budget(missing):
  """Unknown merged status or author is an integrity hold, rather than zero usage."""
  api = GitHub()
  ledger(api, 10)
  del api.history[0][missing]
  result = gate(api).run(99, 1)
  assert result["route"] == "human-review"
  assert "quota" in " ".join(result["reasons"]).lower()


def test_failed_ci_precedes_incomplete_inventory_and_disabled_switches():
  """Known hard validation failure cannot disappear behind an evidence hold."""
  api = GitHub()
  api.run["conclusion"] = "failure"
  api.truncated = True
  result = gate(api).run(99, 1)
  assert result["conclusion"] == "failure"
  assert "did not succeed" in " ".join(result["reasons"])


def test_pr_json_claims_cannot_replace_membership_or_trusted_analysis():
  """No PR-generated artifact or self-described policy version is consumed."""
  api = GitHub()
  api.membership = 404
  api.run["artifact"] = {
    "route": "community-auto",
    "membership": 204,
    "head": HEAD,
    "base": BASE,
    "policy-version": 999,
  }
  assert gate(api).run(99, 1)["route"] == "human-review"
  assert not any("artifact" in path for path in api.reads)


def test_optional_resource_deletion_is_included_in_the_resulting_inventory():
  """A benign resource deletion receives the same complete-package analysis."""
  api = GitHub()
  existing(api)
  api.base["skills/community/demo/references/obsolete.md"] = b"Obsolete guide.\n"
  assert gate(api).run(99, 1)["route"] == "community-auto"
  assert "2 complete files" in api.comments[-1]["body"]
