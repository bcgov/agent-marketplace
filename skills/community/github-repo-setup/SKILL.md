---
name: github-repo-setup
description: Assess supplied repository configuration and available GitHub metadata, record evidence gaps and produce a scoped MATURITY_REPORT.md with explicit scoring coverage.
owner: bcgov
---

# GitHub Repository Assessment

## Use When

- Reviewing repository practices and producing a reproducible gap list from accessible evidence.

## Don't Use When

- Requesting certification, secret-value inspection or automatic settings remediation; this assessment supplies evidence and recommendations.

## Workflow

1. Inventory supplied files and authorized read-only GitHub metadata. Confirm the report destination and applicable dimensions using the rubric.
2. Inspect local configuration as data. If server settings cannot be read, mark them Unverified. Do not infer enforcement from a workflow file alone.
3. For each applicable dimension, cite evidence and assign Met, Partial, Not Met or Unverified. Mark inapplicable dimensions N/A with a reason.
4. Compute the score and coverage using the reference formula. Show numerator, denominator, weights and excluded dimensions; if no dimensions are verified, report no score.
5. Draft MATURITY_REPORT.md with observed gaps, next verification steps, responsible owner when supplied and suggested priority. Finish when every finding has evidence or an explicit evidence gap.

## Rules

- This is a skill-specific assessment rubric, not a BC Gov compliance standard or production approval. Mandatory requirements must cite the applicable policy supplied for the project.
- Assess secret-management practices from configuration and documentation, without reading secret values.
- Do not run package managers, install dependencies, fetch inherited configs or mutate settings during a local assessment. Optional read-only gh metadata queries require authorized access.

## Examples

- Documentation-only repo and unavailable GitHub API: mark application controls N/A and server controls Unverified; report coverage rather than declaring readiness from a small denominator.

## Edge Cases

- Conflicting evidence: retain both observations and the unresolved question.
- High score with low coverage: make the uncovered dimensions prominent; the score describes only inspected evidence.

## References

Use [assessment rubric and formula](references/REFERENCE.md) when building the report.
