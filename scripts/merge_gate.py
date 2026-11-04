"""Pure authorization over trusted facts and inert, trusted-analyzed package data."""

from __future__ import annotations


def login(value: str) -> str:
  """Normalize individual contacts without interpreting teams as individuals."""
  return value.removeprefix("@").casefold()


def decide(facts: dict) -> dict:
  """Return an exact-revision route; hard errors take precedence over switches."""
  result = {
    "head": facts["head"],
    "base": facts["base"],
    "route": "human-review",
    "conclusion": "success",
    "reasons": [],
  }
  if facts["hard-errors"]:
    return {**result, "conclusion": "failure", "reasons": facts["hard-errors"]}
  if facts.get("ineligible"):
    return {
      **result,
      "conclusion": "failure",
      "reasons": ["Contributor eligibility was authoritatively denied."],
    }
  reasons = list(facts["integrity"])
  if facts["dependency"]:
    if not facts["dependency-enabled"]:
      reasons.append("Dependency automation is disabled.")
    if not facts["publication"]:
      reasons.append("Publication is disabled; automatic merges cannot publish.")
    route = "dependency-auto"
  else:
    route = "community-auto"
    if not facts["community-only"] or not facts["packages"]:
      reasons.append(
        "Changes require human review outside eligible Community packages."
      )
    if facts["membership"] != 204:
      reasons.append(
        f"Public bcgov membership is unconfirmed ({facts['membership']}); "
        "an admin must authoritatively confirm eligibility for reviewed changes."
      )
    if not facts["community-enabled"]:
      reasons.append("Community automation is disabled.")
    if not facts["publication"]:
      reasons.append("Publication is disabled; automatic merges cannot publish.")
    if not facts["approved-blockers"]:
      reasons.append("Security's approved blocking set is missing.")
    new_count = sum(item["new-identity"] for item in facts["packages"])
    if facts["quota"] is None or facts["quota"] + new_count > facts["quota-limit"]:
      reasons.append(
        "The author's rolling seven-day new-Extension budget "
        "is unavailable or exceeded."
      )
    risks = {"low": 0, "elevated": 1, "high": 2}
    for package in facts["packages"]:
      if package["requires-human-review"]:
        reasons.append(
          f"{package['id']}: lifecycle, identity or ownership change requires review."
        )
      if risks.get(package["risk"], 99) > risks[facts["risk-ceiling"]]:
        reasons.append(f"{package['id']}: declared risk exceeds the Community ceiling.")
      if not package["new-identity"] and login(facts["author"]) not in {
        login(contact) for contact in package["base-maintainers"] if "/" not in contact
      }:
        reasons.append(f"{package['id']}: author is not an individual base maintainer.")
  return {**result, "route": "human-review" if reasons else route, "reasons": reasons}
