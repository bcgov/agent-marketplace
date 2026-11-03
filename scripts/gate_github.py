"""Main-owned GitHub merge gate: authenticated reads and serialized guarded effects."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import marketplace as m
from gate_data import Incomplete, RepositoryData, package_path, safe_path
from gate_dependency import authorize, workflow
from merge_gate import decide, login
from publication import canonical, git

REPOSITORY = "bcgov/agent-marketplace"
REPOSITORY_ID = 1348843536
WORKFLOW_ID = 365544835
WORKFLOW_PATH = ".github/workflows/pr.yml"
REQUIRED_JOBS = {"fork-gate", "lint-tests", "skills", "marketplace", "results"}
MARKER = "<!-- marketplace-merge-gate -->"


class ApiError(Incomplete):
  """Expose HTTP status without echoing tokens, response payloads or PR data."""

  def __init__(self, status):
    """Retain the actionable status for public-membership holds."""
    self.status = status
    super().__init__(
      f"GitHub API request failed ({status}); "
      "retry or inspect API availability/permissions."
    )


class GitHubApi:
  """Bounded GitHub-only transport using the built-in job token."""

  def request(self, method: str, path: str, data=None, *, status_only=False):
    """Send JSON requests, never execute returned code or trust an arbitrary URL."""
    if not path.startswith((f"repos/{REPOSITORY}/", "orgs/bcgov/public_members/")):
      raise ValueError("Unsupported API authority")
    request = Request(
      "https://api.github.com/" + path,
      data=canonical(data) if data is not None else None,
      method=method,
      headers={
        "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2026-03-10",
      },
    )
    try:
      with urlopen(request, timeout=60) as response:
        content = response.read(16 * 1024 * 1024 + 1)
        if len(content) > 16 * 1024 * 1024:
          raise Incomplete("API response exceeded its bounded size.")
        if status_only:
          return response.status
        return json.loads(content) if content else None
    except HTTPError as exc:
      raise ApiError(exc.code) from None
    except (URLError, TimeoutError) as exc:
      raise ApiError("network error") from exc

  def public_membership(self, author: str):
    """Only HTTP 204 confirms the public-member condition; 404 remains unknown."""
    try:
      return self.request(
        "GET",
        "orgs/bcgov/public_members/" + quote(author, safe=""),
        status_only=True,
      )
    except ApiError as exc:
      return exc.status


class GitHubGate:
  """Evaluate immutable PR data and synchronously merge only a revalidated head.

  The workflow serializes this entire entrypoint in one repository-wide group.
  Native strict-base hard checks protect against manual merges outside that group;
  GitHub's merge endpoint guards the head, but has no expected-base parameter.
  """

  def __init__(self, root: Path, *, api=None, trusted_sha=None, now=None):
    """Bind the trusted main checkout, external API and observation time explicitly."""
    self.root = root
    self.api = api or GitHubApi()
    self.trusted_sha = trusted_sha or git(root, "rev-parse", "HEAD").strip()
    self.now = now or datetime.now(UTC)

  def request(self, method: str, path: str, data=None):
    """Restrict repository operations to the fixed canonical repository."""
    return self.api.request(method, f"repos/{REPOSITORY}/{path}", data)

  def listing(self, path: str, *, key=None, cap=100000) -> list:
    """Read every page and reject caps, inconsistent totals and duplicate pages."""
    values = []
    total = None
    for page in range(1, min(cap // 100 + 2, 1002)):
      separator = "&" if "?" in path else "?"
      response = self.request("GET", f"{path}{separator}per_page=100&page={page}")
      batch = response.get(key) if key and isinstance(response, dict) else response
      if key:
        count = response.get("total_count")
        if not isinstance(count, int) or (total is not None and total != count):
          raise Incomplete("Paginated API totals changed or are unavailable.")
        total = count
      if not isinstance(batch, list) or len(batch) > 100:
        raise Incomplete("Unexpected paginated API response.")
      values.extend(batch)
      if len(values) >= cap:
        raise Incomplete(
          "The API inventory reached its pagination cap; human review is required."
        )
      if len(batch) < 100:
        if total is not None and len(values) != total:
          raise Incomplete("Paginated API inventory is incomplete.")
        identifiers = [item.get("id") for item in values if "id" in item]
        if len(identifiers) != len(set(identifiers)):
          raise Incomplete("Paginated API inventory contains repeated records.")
        return values
    raise Incomplete("The API inventory exceeded bounded pagination.")

  def origin(self, run_id: int, attempt: int):
    """Authenticate provider run/attempt/workflow/repository before resolving a PR."""
    latest = self.request("GET", f"actions/runs/{run_id}")
    run = self.request("GET", f"actions/runs/{run_id}/attempts/{attempt}")
    expected = {
      "id": run_id,
      "run_attempt": attempt,
      "workflow_id": WORKFLOW_ID,
      "path": WORKFLOW_PATH,
      "event": "pull_request",
      "status": "completed",
    }
    if (
      latest.get("id") != run_id
      or latest.get("run_attempt") != attempt
      or any(run.get(field) != value for field, value in expected.items())
    ):
      raise Incomplete(
        "Run origin/attempt is unexpected or superseded; retry the current PR workflow."
      )
    if (
      run.get("repository", {}).get("id") != REPOSITORY_ID
      or run["repository"].get("full_name") != REPOSITORY
    ):
      raise Incomplete("Unexpected run repository.")
    registered = self.request("GET", f"actions/workflows/{WORKFLOW_ID}")
    if (
      registered.get("id") != WORKFLOW_ID
      or registered.get("path") != WORKFLOW_PATH
      or registered.get("state") != "active"
    ):
      raise Incomplete("Expected numeric PR workflow is unavailable.")
    associations = run.get("pull_requests", [])
    integrity = []
    if not associations:
      # Some fork contexts omit historical associations. Resolve a current PR only
      # for a routing hold; this lookup cannot manufacture the missing tested base.
      associations = [
        item
        for item in self.listing(f"commits/{run['head_sha']}/pulls")
        if item.get("state") == "open"
        and item.get("head", {}).get("sha") == run["head_sha"]
        and item.get("base", {}).get("repo", {}).get("id") == REPOSITORY_ID
      ]
      integrity.append(
        "Historical tested-base association is unavailable for this run; "
        "obtain a new authoritative PR run before automatic merge."
      )
    if len(associations) != 1:
      raise Incomplete("Run cannot be bound to exactly one pull request.")
    association = associations[0]
    number = association.get("number")
    if not isinstance(number, int) or number <= 0:
      raise Incomplete("Provider PR association is malformed.")
    pr = self.request("GET", f"pulls/{number}")
    if pr.get("state") != "open" or pr.get("head", {}).get("sha") != run.get(
      "head_sha"
    ):
      raise Incomplete(
        "PR is closed, draft or superseded; no current-head write is authorized."
      )
    if pr.get("draft"):
      integrity.append("Draft pull requests require human review before merge.")
    if (
      pr["base"]["repo"].get("id") != REPOSITORY_ID
      or pr["base"]["repo"].get("full_name") != REPOSITORY
      or pr["base"]["ref"] != "main"
    ):
      raise Incomplete("PR must target the canonical repository's main branch.")
    if (
      association.get("head", {}).get("sha") != pr["head"]["sha"]
      or association.get("head", {}).get("repo", {}).get("id")
      != pr["head"]["repo"]["id"]
      or run.get("head_repository", {}).get("id") != pr["head"]["repo"]["id"]
    ):
      raise Incomplete("Run's associated head repository/revision is inconsistent.")
    return run, pr, association, integrity

  def quota(self, data: RepositoryData, author: str, days: int) -> int:
    """Count new canonical identities by authoritative merged PR author/time.

    Closed PR history is fully paginated, never inferred from lagging search.
    First merge parent is the actual mainline before both squash and merge commits;
    source commit count and historical PR base are not that mainline inventory.
    """
    since = self.now - timedelta(days=days)
    count = 0
    history = self.listing("pulls?state=closed&sort=updated&direction=desc", cap=10000)
    for summary in history:
      if "merged_at" not in summary:
        raise Incomplete("Author quota history lacks authoritative merged status.")
      merged_at = summary.get("merged_at")
      if not merged_at:
        continue
      merged = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
      if merged < since:
        continue
      recorded_author = summary.get("user", {}).get("login")
      if not isinstance(recorded_author, str) or not recorded_author:
        raise Incomplete("Author quota history lacks authoritative PR author identity.")
      if merged > self.now:
        raise Incomplete("Author quota includes a merge after this observation; retry.")
      if login(recorded_author) != login(author):
        continue
      pr = self.request("GET", f"pulls/{summary['number']}")
      if (
        not pr.get("merged")
        or pr.get("merged_at") != merged_at
        or login(pr["user"]["login"]) != login(author)
        or pr["base"]["ref"] != "main"
        or pr["base"]["repo"]["id"] != REPOSITORY_ID
      ):
        raise Incomplete("Merged PR author/time/base attribution is inconsistent.")
      revision = pr["merge_commit_sha"]
      commit = self.request("GET", f"git/commits/{revision}")
      parents = commit.get("parents", [])
      if commit.get("sha") != revision or len(parents) not in {1, 2}:
        raise Incomplete("Merged PR topology cannot establish the rolling quota.")
      before, after = data.records(parents[0]["sha"]), data.records(revision)
      if not before.keys() <= after.keys():
        raise Incomplete(
          "Historical identity reservations are incomplete; author quota needs review."
        )
      count += sum(
        record["specialty"] == "community"
        for identity, record in after.items()
        if identity not in before
      )
    return count

  def gather(
    self, run: dict, pr: dict, association: dict, integrity: list[str]
  ) -> dict:
    """Recompute authorization from immutable complete data and current base facts."""
    head = pr["head"]["sha"]
    base = self.request("GET", "git/ref/heads/main")["object"]["sha"]
    facts = {
      "head": head,
      "base": base,
      "author": pr["user"]["login"],
      "integrity": list(integrity),
      "hard-errors": [],
      "packages": [],
      "membership": "not checked",
      "quota": None,
      "quota-limit": 10,
      "risk-ceiling": "elevated",
      "community-only": False,
      "dependency": False,
      "publication": False,
      "community-enabled": False,
      "dependency-enabled": False,
      "approved-blockers": False,
    }
    if run.get("conclusion") != "success":
      facts["hard-errors"].append("Authenticated PR workflow did not succeed.")
    data = RepositoryData(self.request)
    try:
      if base != self.trusted_sha:
        facts["integrity"].append(
          "Trusted main advanced beyond this gate checkout; "
          "rerun the gate against current main."
        )
      if (
        association["base"].get("sha") != base
        or association["base"].get("repo", {}).get("id") != REPOSITORY_ID
      ):
        facts["integrity"].append(
          "PR CI tested a different base; update the PR and rerun validation."
        )
      changes = self.listing(f"pulls/{pr['number']}/files", cap=3000)
      if len(changes) != pr.get("changed_files"):
        raise Incomplete("Changed-file pagination disagrees with the PR inventory.")
      if len({item.get("filename") for item in changes}) != len(changes):
        raise Incomplete("Changed-file pagination contains repeated paths.")
      changed = set()
      for item in changes:
        if item.get("status") not in {
          "added",
          "modified",
          "removed",
          "renamed",
          "copied",
          "changed",
          "unchanged",
        } or not safe_path(item.get("filename")):
          raise Incomplete("Changed-file metadata is unsupported or incomplete.")
        changed.add(item["filename"])
        if item["status"] == "renamed":
          if not safe_path(item.get("previous_filename")):
            raise Incomplete("Both sides of a rename must be available.")
          changed.add(item["previous_filename"])
      base_tree, head_tree = data.tree(base), data.tree(head)
      # Independent immutable-tree comparison catches omitted files, including
      # Manifest-only diffs that omit a resource or a removed package side.
      actual = {
        path
        for path in base_tree.keys() | head_tree.keys()
        if base_tree.get(path, {}).get("type") != "tree"
        and head_tree.get(path, {}).get("type") != "tree"
        and (base_tree.get(path, {}).get("sha"), base_tree.get(path, {}).get("mode"))
        != (head_tree.get(path, {}).get("sha"), head_tree.get(path, {}).get("mode"))
      }
      if actual != changed:
        raise Incomplete(
          "Changed-file metadata does not cover the complete immutable tree difference."
        )
      analysis = data.analyze(self.root, base, head, changed)
      facts["hard-errors"].extend(analysis["hard-errors"])
      facts.update({key: analysis[key] for key in ("packages", "analyses", "engine")})
      config = analysis["config"]
      community = config.get("community-intake", {})
      facts.update(
        {
          "publication": config.get("publication", {}).get("enabled", False),
          "community-enabled": community.get("auto-publish", False),
          "dependency-enabled": config.get("dependency-intake", {}).get(
            "auto-merge", False
          ),
          "approved-blockers": bool(analysis["policy"]["blocking"]),
          "risk-ceiling": community.get("auto-publish-risk-ceiling", "elevated"),
          "quota-limit": community.get("max-new-packages-per-window", 10),
          "community-only": bool(changed)
          and all(
            package_path(path) and path.split("/")[1] == "community" for path in changed
          ),
        }
      )
      jobs = self.listing(
        f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs", key="jobs"
      )
      names = [job.get("name") for job in jobs]
      if any(names.count(name) != 1 for name in REQUIRED_JOBS):
        facts["integrity"].append(
          "Required jobs are missing or ambiguous "
          "in the authenticated workflow attempt."
        )
      for job in jobs:
        if job.get("name") not in REQUIRED_JOBS:
          continue
        if job.get("run_id") != run["id"] or job.get("head_sha") != head:
          facts["integrity"].append(
            "Required job provenance does not match the authenticated run/head."
          )
        if job.get("status") != "completed" or job.get("conclusion") != "success":
          facts["hard-errors"].append("Required PR validation did not succeed.")
      if pr["user"].get("id") == 49699333:
        commit = self.request("GET", f"commits/{head}")
        facts["dependency"] = authorize(pr, commit, data, base, head, changed)
      before_workflow = data.blob(base_tree[WORKFLOW_PATH])
      after_workflow = data.blob(head_tree[WORKFLOW_PATH])
      if before_workflow != after_workflow and not facts["dependency"]:
        facts["integrity"].append(
          "Proposed PR workflow cannot establish its own authorization; "
          "trusted workflow semantics changed."
        )
      trusted_workflow = workflow(before_workflow)
      if "pull_request" not in trusted_workflow.get("on", {}):
        facts["integrity"].append(
          "Trusted workflow does not establish default PR test-merge provenance."
        )
      for name in ("lint-tests", "skills", "marketplace"):
        checkouts = [
          step
          for step in trusted_workflow["jobs"][name]["steps"]
          if step.get("uses", "").startswith("actions/checkout@")
        ]
        if len(checkouts) != 1 or set(checkouts[0].get("with", {})) - {"fetch-depth"}:
          facts["integrity"].append(
            "Trusted checkout does not establish the default tested merge."
          )
      merge = self.request("GET", f"git/commits/{pr['merge_commit_sha']}")
      if merge.get("sha") != pr["merge_commit_sha"] or [
        item.get("sha") for item in merge.get("parents", [])
      ] != [base, head]:
        facts["integrity"].append(
          "Test-merge parents do not map to the exact current base and PR head."
        )
      if not facts["dependency"]:
        facts["membership"] = self.api.public_membership(pr["user"]["login"])
        facts["quota"] = self.quota(
          data, pr["user"]["login"], community.get("window-days", 7)
        )
    except Incomplete as exc:
      facts["integrity"].append(str(exc))
    except m.MarketplaceError:
      facts["hard-errors"].append(
        "Trusted validation rejected a Manifest, policy or package inventory. "
        "Correct the package or request administrator review."
      )
    except (KeyError, ValueError, TypeError, UnicodeError):
      facts["integrity"].append(
        "Required provider/configuration facts are malformed or unavailable; "
        "retry or request administrator review."
      )
    return facts

  def current(self, number: int, head: str, base: str) -> bool:
    """Guard each diagnostic/effect against superseded heads and base changes."""
    pr = self.request("GET", f"pulls/{number}")
    return (
      pr.get("state") == "open"
      and not pr.get("draft")
      and pr.get("head", {}).get("sha") == head
      and self.request("GET", "git/ref/heads/main")["object"]["sha"] == base
    )

  def diagnostic(self, pr: dict, result: dict, facts: dict, *, after_merge=False):
    """Idempotently post head-specific routing evidence and base-contact diagnostics."""
    head, number = result["head"], pr["number"]
    current = self.request("GET", f"pulls/{number}")
    if current["head"]["sha"] != head or (
      not after_merge and current.get("state") != "open"
    ):
      return
    body = "\n".join(
      [
        f"Route: **{result['route']}**",
        f"Head: `{head}`",
        f"Trusted base: `{result['base']}`",
        *[f"- {reason}" for reason in result["reasons"]],
      ]
    )
    contacts = sorted(
      {
        contact if contact.startswith("@") else "@" + contact
        for package in facts.get("packages", [])
        if not package["new-identity"]
        for contact in package["base-maintainers"]
        if re.fullmatch(r"@?[A-Za-z0-9-]+(?:/[A-Za-z0-9_-]+)?", contact)
      }
    )
    if contacts:
      body += "\nBase contacts: " + ", ".join(contacts)
    for identity, analysis in sorted(facts.get("analyses", {}).items()):
      body += (
        f"\nPackage `{identity}`: `{analysis['package-tree-digest']}` "
        f"({len(analysis['files'])} complete files)."
      )
    if facts.get("engine"):
      body += f"\nTrusted engine/policy inputs: `{facts['engine']}`."
    body += (
      "\nRetry: rerun the current PR workflow or dispatch merge-gate "
      "with its run ID/attempt."
    )
    external = f"merge-gate:{number}:{head}"
    checks = self.listing(f"commits/{head}/check-runs", key="check_runs")
    own = [
      check
      for check in checks
      if check.get("name") == "merge-gate"
      and check.get("external_id") == external
      and check.get("app", {}).get("slug") == "github-actions"
    ]
    payload = {
      "name": "merge-gate",
      "head_sha": head,
      "external_id": external,
      "status": "completed",
      "conclusion": result["conclusion"],
      "output": {"title": result["route"], "summary": body[:60000]},
    }
    if own:
      same = all(
        own[-1].get(key) == value for key, value in payload.items() if key != "output"
      ) and all(
        own[-1].get("output", {}).get(key) == value
        for key, value in payload["output"].items()
      )
      if not same:
        self.request("PATCH", f"check-runs/{own[-1]['id']}", payload)
    else:
      self.request("POST", "check-runs", payload)
    comments = self.listing(f"issues/{number}/comments")
    marker = f"{MARKER}\n<!-- head:{head} -->\n"
    comment = marker + body
    own_comments = [
      item
      for item in comments
      if item.get("user", {}).get("login") == "github-actions[bot]"
      and item.get("body", "").startswith(marker)
    ]
    if own_comments:
      if own_comments[-1]["body"] != comment:
        self.request(
          "PATCH", f"issues/comments/{own_comments[-1]['id']}", {"body": comment}
        )
    else:
      self.request("POST", f"issues/{number}/comments", {"body": comment})

  def run(self, run_id: int, attempt: int) -> dict:
    """Handle a completion/retry without arming deferred native auto-merge."""
    try:
      run, pr, association, integrity = self.origin(run_id, attempt)
    except (Incomplete, KeyError, TypeError, ValueError) as exc:
      return {
        "route": "human-review",
        "conclusion": "success",
        "reasons": [str(exc)],
        "write": False,
      }
    facts = self.gather(run, pr, association, integrity)
    result = decide(facts)
    if result["route"] != "human-review" and result["conclusion"] == "success":
      # All executions share the workflow's repository-wide mutation queue.
      # Fetch every fact again INSIDE that serialization immediately before merge.
      try:
        run, fresh, association, integrity = self.origin(run_id, attempt)
      except (Incomplete, KeyError, TypeError, ValueError):
        return {
          **result,
          "route": "human-review",
          "reasons": ["Superseded before final authorization."],
          "write": False,
        }
      facts = self.gather(run, fresh, association, integrity)
      result = decide(facts)
      pr = fresh
      if result["route"] != "human-review" and result["conclusion"] == "success":
        if not self.current(pr["number"], result["head"], result["base"]):
          return {
            **result,
            "route": "human-review",
            "reasons": ["Head/base changed before merge; rerun current validation."],
            "write": False,
          }
        self.diagnostic(pr, result, facts)
        # One more current-state read follows diagnostics and immediately precedes
        # the expected-head merge. No deferred permission survives this decision.
        if not self.current(pr["number"], result["head"], result["base"]):
          return {
            **result,
            "route": "human-review",
            "reasons": ["Head/base changed before merge."],
            "write": False,
          }
        try:
          merged = self.request(
            "PUT",
            f"pulls/{pr['number']}/merge",
            {"sha": result["head"], "merge_method": "squash"},
          )
          if not merged.get("merged"):
            raise Incomplete(
              "Guarded merge was refused; inspect native hard checks "
              "and rerun current validation."
            )
        except (Incomplete, RuntimeError):
          result = {
            **result,
            "route": "human-review",
            "reasons": [
              "Guarded merge was refused or raced with a newer revision; "
              "inspect native hard checks and retry."
            ],
          }
          self.diagnostic(pr, result, facts)
          return result
        try:
          dispatch = self.request(
            "POST",
            "actions/workflows/publish.yml/dispatches",
            {"ref": "main", "inputs": {"mode": "reconcile"}},
          )
          if not isinstance(dispatch, dict) or not dispatch.get("workflow_run_id"):
            raise Incomplete(
              "Publish dispatch did not return its documented run identity."
            )
          result["reasons"] = [
            "Merged exact authorized head; publication dispatched "
            f"(run {dispatch['workflow_run_id']}). "
            "Dispatch is not publication success."
          ]
        except (Incomplete, RuntimeError):
          result["reasons"] = [
            "Merged exact authorized head, but publish dispatch failed. "
            "Manually run publish.yml with mode reconcile on main; "
            "inspect Actions for a dispatch that may have succeeded before timeout."
          ]
        self.diagnostic(pr, result, facts, after_merge=True)
        return result
    # A stale completion never writes a check/comment on a newer PR head.
    self.diagnostic(pr, result, facts)
    return result


def main():
  """Read only provider run coordinates; all PR and policy authority comes from APIs."""
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--run-id", type=int, required=True)
  parser.add_argument("--attempt", type=int, required=True)
  args = parser.parse_args()
  if args.run_id <= 0 or args.attempt <= 0:
    parser.error("Run ID and attempt must be positive integers")
  result = GitHubGate(Path(__file__).resolve().parents[1]).run(
    args.run_id, args.attempt
  )
  print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
  main()
