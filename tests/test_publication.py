"""Behavior at the deterministic Catalogue and guarded publication boundaries."""

import copy
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import publication as p


def candidate(sha="a" * 40):
  """Use realistic pinned links and preserve author-authored SHA metadata."""
  return {
    "schema-version": "bcgov-marketplace/v1",
    "repository": "https://github.com/bcgov/agent-marketplace",
    "revision": sha,
    "version": "source",
    "engine": "sha256:engine-v1",
    "legacy-ids": {"legacy/demo": "skill/demo"},
    "extensions": [
      {
        "id": "skill/demo",
        "lifecycle": "active",
        "content-digest": "sha256:one",
        "summary": "Author pin " + "a" * 40,
        "source": {
          "repository": "https://github.com/bcgov/agent-marketplace",
          "revision": sha,
          "path": "skills/community/demo",
        },
        "install-options": [
          {
            "client": "VS Code Local",
            "source": {
              "repository": "https://github.com/bcgov/agent-marketplace",
              "revision": sha,
              "path": "skills/community/demo",
            },
            "source-url": f"https://github.com/bcgov/agent-marketplace/tree/{sha}/skills/community/demo",
            "placements": [
              {
                "source": "SKILL.md",
                "destination": ".github/skills/demo/SKILL.md",
                "sha256": "a" * 64,
              }
            ],
          }
        ],
      }
    ],
  }


def test_docs_only_pinned_coordinates_are_neutral_but_actual_inputs_are_meaningful():
  """Generated pins change independently of policy, adapters and authored values."""
  old = candidate()
  new = candidate("b" * 40)
  assert p.meaningful(old) == p.meaningful(new)
  for field in ("engine", "summary", "install-options"):
    changed = copy.deepcopy(new)
    target = changed if field == "engine" else changed["extensions"][0]
    if field == "install-options":
      target[field][0]["client"] = "changed"
    else:
      target[field] = "changed"
    assert p.meaningful(old) != p.meaningful(changed)


class Remote:
  """Model external immutable release/Pages APIs and failures after persistence."""

  def __init__(self):
    """Start with a deliberately registered legacy snapshot."""
    legacy = {
      "schema-version": "bcgov-marketplace-catalog/v1alpha1",
      "extensions": [{"id": "legacy/demo"}],
    }
    self.baseline = {
      "tag": "catalog-2026.10.01",
      "target": "0" * 40,
      "digest": p.digest(p.canonical(legacy)),
      "ids": ["legacy/demo"],
    }
    self.items = [
      p.Release(
        self.baseline["tag"],
        "0" * 40,
        p.canonical(legacy),
        False,
        "2026-10-01T00:00:00Z",
      )
    ]
    self.on = True
    self.effects = []
    self.live = None
    self.fault = None
    self.disable_at = None

  def enabled(self):
    """Read current trusted main, independently of a candidate or old attempt."""
    return self.on

  def is_descendant(self, older, newer):
    """Model a linear main source history in the external SCM fixture."""
    return older <= newer

  def releases(self):
    """Return all remote publications and incomplete drafts."""
    return list(self.items)

  def tags(self):
    """Expose tag targets independently of release target_commitish."""
    return {r.tag: r.sha for r in self.items}

  def prepare_site(self, content, site):
    """Validate site inputs before publication effects."""
    assert json.loads(content)["schema-version"] == "bcgov-marketplace/v1"
    if self.disable_at == "prepared":
      self.on = False

  def create(self, tag, sha, notes):
    """Persist an incomplete draft pinned to a full source SHA."""
    self.effects.append("create")
    self.items.append(p.Release(tag, sha, None, True, None))
    return self.items[-1]

  def upload(self, release, content):
    """Persist exact bytes, optionally failing after the server accepted them."""
    self.effects.append("upload")
    if self.fault == "upload-before":
      self.fault = None
      raise OSError("upload failed before persistence")
    self.items[self.items.index(release)] = replace(release, content=content)
    if self.disable_at == "uploaded":
      self.on = False
    if self.fault == "upload":
      self.fault = None
      raise OSError("upload timeout after success")

  def publish(self, release):
    """Publish without ever replacing uploaded bytes."""
    self.effects.append("publish")
    if self.fault == "publish-before":
      self.fault = None
      raise OSError("publish failed before persistence")
    self.items[self.items.index(release)] = replace(
      release, draft=False, published_at="2026-11-03T01:02:03Z"
    )
    if self.fault == "publish":
      self.fault = None
      raise OSError("publish timeout after success")

  def deploy(self, content, site):
    """Expose the deployed bytes and actual successful deployment record."""
    self.effects.append("deploy")
    if self.fault == "deploy":
      self.fault = None
      raise OSError("Pages failed")
    self.live = content
    return {"id": "deployment-1", "status": "succeeded"}


def publish(remote, data=None, **kwargs):
  """Exercise the coordinator using an external adapter, never internal mocks."""
  return p.publish(
    remote,
    data or candidate(),
    {"source": "b" * 40, "run": "123"},
    baseline=remote.baseline,
    day="2026.11.03",
    **kwargs,
  )


def test_first_v1_migration_then_docs_only_reuses_exact_asset():
  """First-v1 explicitly records its baseline; docs retain old snapshot pins."""
  remote = Remote()
  first = publish(remote)
  assert first.action == "publish"
  assert remote.live == first.content == remote.items[-1].content
  asset = json.loads(first.content)
  assert asset["publication"]["migration"]["tag"] == "catalog-2026.10.01"
  assert asset["revision"] == "a" * 40
  second = publish(remote, candidate("b" * 40))
  assert second.action == "reuse"
  assert second.content == first.content
  assert second.site["source"] == "b" * 40
  assert remote.effects == ["create", "upload", "publish", "deploy", "deploy"]


@pytest.mark.parametrize(
  "fault", ["upload", "publish", "deploy", "upload-before", "publish-before"]
)
def test_retry_resumes_persisted_state_without_duplicate_snapshot(fault):
  """Timeouts after accepted effects and Pages failures reuse immutable bytes."""
  remote = Remote()
  remote.fault = fault
  with pytest.raises(OSError):
    publish(remote)
  result = publish(remote)
  assert len(remote.items) == 2
  assert remote.live == result.content
  assert remote.effects.count("create") == 1
  assert remote.effects.count("upload") == (2 if fault == "upload-before" else 1)


@pytest.mark.parametrize("disable_at", ["initial", "prepared", "uploaded"])
def test_current_main_disable_stops_queued_and_recovery_effects(disable_at):
  """Historical enabled flags cannot override the current trusted main switch."""
  remote = Remote()
  remote.disable_at = disable_at
  remote.on = disable_at != "initial"
  result = publish(remote)
  assert result.action == "disabled"
  assert "publish" not in remote.effects
  assert "deploy" not in remote.effects


def test_source_dates_use_first_parent_committer_time_and_stable_identity(tmp_path):
  """Baseline dates are unknown; transfers preserve addition and renames add."""

  def git(*args, day=1):
    """Make real source history with an author date distinct from committer UTC."""
    env = {
      **os.environ,
      "GIT_AUTHOR_DATE": "2020-01-01T00:00:00Z",
      "GIT_COMMITTER_DATE": f"2026-10-{day:02}T23:00:00-07:00",
    }
    return (
      subprocess.check_output(["git", "-C", str(tmp_path), *args], env=env)
      .decode()
      .strip()
    )

  git("init")
  git("config", "user.email", "test@example.com")
  git("config", "user.name", "Test")
  git("config", "commit.gpgsign", "false")
  old = tmp_path / "skills/community/old"
  old.mkdir(parents=True)
  (old / "bcgov-extension.yaml").write_text("maintainers: ['@bcgov/test']\n")
  (old / "SKILL.md").write_text("Original")
  git("add", ".")
  git("commit", "-m", "baseline")
  baseline = git("rev-parse", "HEAD")
  assert p.source_dates(tmp_path, baseline)["bcgov-public/skill/old"] == {
    "added": None,
    "updated": None,
  }
  (old / "SKILL.md").write_text("Changed")
  git("add", ".")
  git("commit", "-m", "edit", day=2)
  moved = tmp_path / "skills/security/old"
  moved.parent.mkdir()
  old.rename(moved)
  git("add", "-A")
  git("commit", "-m", "transfer", day=3)
  dates = p.source_dates(tmp_path, baseline)
  assert dates["bcgov-public/skill/old"] == {
    "added": None,
    "updated": "2026-10-04T06:00:00Z",
  }
  moved.rename(moved.with_name("new"))
  git("add", "-A")
  git("commit", "-m", "real rename", day=4)
  dates = p.source_dates(tmp_path, baseline)
  assert dates["bcgov-public/skill/new"] == {
    "added": "2026-10-05T06:00:00Z",
    "updated": "2026-10-05T06:00:00Z",
  }
  tombstone = moved.with_name("new")
  (tombstone / "bcgov-extension.yaml").write_text(
    "lifecycle: removed\nnotice: Retired\n"
  )
  (tombstone / "SKILL.md").unlink()
  git("add", "-A")
  git("commit", "-m", "tombstone edit", day=5)
  assert p.source_dates(tmp_path, baseline)["bcgov-public/skill/new"] == {
    "added": "2026-10-05T06:00:00Z",
    "updated": "2026-10-06T06:00:00Z",
  }
  with pytest.raises(p.PublicationError, match="history-start"):
    p.source_dates(tmp_path, "f" * 40)


def test_withdrawal_supersedes_old_live_retry_and_site_rollback_keeps_newest():
  """S1 stays downloadable but cannot replace S2 after withdrawal."""
  remote = Remote()
  first = publish(remote)
  withdrawn = candidate("b" * 40)
  withdrawn["extensions"][0]["lifecycle"] = "removed"
  withdrawn["extensions"][0]["install-options"] = []
  remote.fault = "deploy"
  with pytest.raises(OSError):
    publish(remote, withdrawn)
  newest_release = remote.items[-1]
  with pytest.raises(p.PublicationError, match="Superseded"):
    p.guard_deploy(remote, first.release, remote.baseline)
  recovered = publish(remote, recover=True)
  assert recovered.content == newest_release.content == remote.live
  assert json.loads(recovered.content)["extensions"][0]["lifecycle"] == "removed"
  assert first.content == remote.items[1].content
  assert len(remote.items) == 3


def test_old_failed_deploy_retry_cannot_publish_a_fresh_active_replay():
  """Only a reviewed descendant source change can supersede a withdrawal."""
  remote = Remote()
  remote.fault = "deploy"
  with pytest.raises(OSError):
    publish(remote)
  withdrawal = candidate("b" * 40)
  withdrawal["extensions"][0]["lifecycle"] = "removed"
  withdrawal["extensions"][0]["install-options"] = []
  latest = publish(remote, withdrawal)
  with pytest.raises(p.PublicationError, match="Stale source"):
    publish(remote, candidate())
  assert len(remote.items) == 3
  assert remote.live == latest.content


def test_accepted_history_rejects_a_backward_source_disguised_as_a_new_release():
  """An apparent new lineage tag cannot authorize replaying pre-withdrawal source."""
  remote = Remote()
  first = publish(remote)
  withdrawal = candidate("b" * 40)
  withdrawal["extensions"][0]["lifecycle"] = "removed"
  withdrawal["extensions"][0]["install-options"] = []
  latest = publish(remote, withdrawal)
  replay = json.loads(first.content)
  replay["version"] = "catalog-2026.11.03.3"
  replay["publication"]["parent"] = {
    "tag": latest.release.tag,
    "digest": p.digest(latest.content),
  }
  remote.items.append(
    p.Release(
      replay["version"], "a" * 40, p.canonical(replay), False, "2026-11-03T03:00:00Z"
    )
  )
  with pytest.raises(p.PublicationError, match="ancestry"):
    p.newest(remote, remote.baseline)


def test_asset_collision_is_an_error_and_missing_history_never_resets():
  """Untrusted or mismatched remote state fails before immutable mutation."""
  remote = Remote()
  remote.fault = "upload"
  with pytest.raises(OSError):
    publish(remote)

  remote.items[-1] = replace(remote.items[-1], content=b"different bytes")
  with pytest.raises(p.PublicationError, match="collision"):
    publish(remote)
  assert "publish" not in remote.effects
  remote.items = []
  with pytest.raises(p.PublicationError, match="legacy baseline"):
    publish(remote)


def test_mismatched_draft_sha_and_tag_target_fail_without_mutation():
  """A matching attempt cannot repair somebody else's tag or draft by overwriting."""
  remote = Remote()
  remote.fault = "upload"
  with pytest.raises(OSError):
    publish(remote)
  original = remote.items[-1]
  remote.items[-1] = replace(original, sha="f" * 40)
  with pytest.raises(p.PublicationError, match="source SHA differs"):
    publish(remote)
  assert remote.effects == ["create", "upload"]

  remote.items[-1] = original
  remote.tags = lambda: {original.tag: "f" * 40}
  with pytest.raises(p.PublicationError, match="Tag target collision"):
    publish(remote)
  assert remote.effects == ["create", "upload"]


def test_matching_orphan_tag_resumes_and_occupied_refs_allocate_next_free_tag():
  """Refs without releases participate in allocation and matching-tag recovery."""
  remote = Remote()
  remote.tags = lambda: {"catalog-2026.11.03": "a" * 40}
  resumed = publish(remote)
  assert resumed.release.tag == "catalog-2026.11.03"
  occupied = Remote()
  occupied.tags = lambda: {
    "catalog-2026.11.03": "f" * 40,
    "catalog-2026.11.03.2": "e" * 40,
  }
  result = publish(occupied)
  assert result.release.tag == "catalog-2026.11.03.3"


@pytest.mark.parametrize("change", ["digest", "owner", "policy", "engine"])
def test_meaningful_package_or_evidence_change_allocates_one_snapshot(change):
  """Policy/owner evidence updates publish even when package bytes are unchanged."""
  remote = Remote()
  publish(remote)
  changed = candidate()
  if change == "digest":
    changed["extensions"][0]["content-digest"] = "sha256:two"
  elif change == "owner":
    changed["specialties"] = [{"id": "security", "owner-team": "@bcgov/new-owner"}]
  else:
    changed[change] = "updated"
  result = publish(remote, changed)
  assert result.release.tag == "catalog-2026.11.03.2"
  assert remote.live == remote.items[-1].content
  assert publish(remote, changed).action == "reuse"
