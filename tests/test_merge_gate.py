"""Trusted merge routing decisions through the public decision interface."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from merge_gate import decide


def eligible():
  """Return independently established eligible Community edit facts."""
  return {
    "head": "a" * 40,
    "base": "b" * 40,
    "author": "Alice",
    "integrity": [],
    "hard-errors": [],
    "membership": 204,
    "quota": 9,
    "community-only": True,
    "dependency": False,
    "publication": True,
    "community-enabled": True,
    "dependency-enabled": False,
    "approved-blockers": True,
    "quota-limit": 10,
    "risk-ceiling": "elevated",
    "packages": [
      {
        "id": "bcgov-public/skill/demo",
        "new-identity": False,
        "base-maintainers": ["@ALICE"],
        "requires-human-review": False,
        "risk": "low",
      }
    ],
  }


def test_valid_edit_uses_base_individual_contact_and_exact_revision():
  """Base individual maintainers can take the Community automatic route."""
  result = decide(eligible())
  assert result == {
    "route": "community-auto",
    "conclusion": "success",
    "reasons": [],
    "head": "a" * 40,
    "base": "b" * 40,
  }


@pytest.mark.parametrize(
  "changes,reason",
  [
    ({"membership": 404}, "unconfirmed (404)"),
    ({"membership": 403}, "unconfirmed (403)"),
    ({"membership": "network error"}, "unconfirmed (network error)"),
    ({"community-enabled": False}, "Community automation is disabled"),
    ({"approved-blockers": False}, "approved blocking set"),
    ({"publication": False}, "Publication is disabled"),
    ({"community-only": False}, "outside eligible Community"),
    ({"integrity": ["Missing tested base"]}, "Missing tested base"),
    ({"quota": None}, "budget"),
  ],
)
def test_review_holds_pass_without_automatic_authorization(changes, reason):
  """Unconfirmed eligibility produces a successful and actionable review hold."""
  result = decide({**eligible(), **changes})
  assert result["route"] == "human-review"
  assert result["conclusion"] == "success"
  assert any(reason in value for value in result["reasons"])


@pytest.mark.parametrize("contact", ["@bcgov/team", "Bob"])
def test_team_and_self_added_head_contacts_do_not_grant_edit_eligibility(contact):
  """Only an individual contact in the base can authorize an automatic edit."""
  facts = eligible()
  facts["packages"][0]["base-maintainers"] = [contact]
  facts["packages"][0]["maintainers"] = ["Alice"]
  assert decide(facts)["route"] == "human-review"


def test_hard_block_precedes_all_disabled_controls_and_integrity_holds():
  """Disabling publication cannot conceal actual validation failures."""
  result = decide(
    {
      **eligible(),
      "hard-errors": ["undeclared-network"],
      "publication": False,
      "community-enabled": False,
      "integrity": ["No CI receipt"],
    }
  )
  assert result["conclusion"] == "failure"
  assert result["reasons"] == ["undeclared-network"]


def test_independently_confirmed_ineligible_contributors_are_blocked():
  """A public-membership 404 is unknown; authoritative ineligibility is a block."""
  assert decide({**eligible(), "ineligible": True})["conclusion"] == "failure"


@pytest.mark.parametrize(
  "publication,enabled,route",
  [
    (True, True, "dependency-auto"),
    (False, True, "human-review"),
    (True, False, "human-review"),
  ],
)
def test_dependency_route_has_independent_switch_and_shared_publication(
  publication, enabled, route
):
  """Dependency authorization does not borrow Community membership or blockers."""
  facts = {
    **eligible(),
    "dependency": True,
    "dependency-enabled": enabled,
    "publication": publication,
    "community-enabled": False,
    "membership": 404,
    "approved-blockers": False,
  }
  assert decide(facts)["route"] == route


def test_batch_quota_includes_every_new_canonical_identity():
  """Eleven new identities fail even with an empty historical budget."""
  facts = eligible()
  facts["quota"] = 0
  facts["packages"] = [{**facts["packages"][0], "new-identity": True}] * 11
  assert decide(facts)["route"] == "human-review"
