---
name: github-actions
description: Review or draft GitHub Actions workflows for least privilege, untrusted inputs, fork validation, action pinning and independent required checks.
owner: bcgov
---

# GitHub Actions

## Use When

- Authoring a workflow or reviewing permissions, PR trust boundaries and required checks.

## Don't Use When

- Deploying infrastructure or changing repository settings without authorization; prepare a reviewable recommendation first.

## Workflow

1. Identify events, token permissions, source revisions, runner requirements and repository-required checks. Record observed settings separately from recommendations.
2. Start with workflow permissions: {} and give each job only its required permissions. Keep fork PR validation unprivileged, with read-only contents access when needed. Repository approval policy may delay a fork run; it is not a reason to reject every fork.
3. Inspect each action and pin it to a reviewed full commit SHA when immutable source pinning is required. A major tag is movable; describe any accepted tag policy as a repository choice.
4. Pass untrusted PR text through environment variables or structured arguments, then quote it for the receiving command. Inspect shell construction and avoid interpolating expressions directly into run scripts.
5. Separate privileged effects into trusted code. A completion event alone is not authorization: check its origin and exact tested revision before any effect; never execute PR content with a privileged token.
6. Deliver the workflow diff, trust-boundary explanation and validation evidence. Keep independent hard/security/routing checks required as repository policy demands; an aggregator may supplement them.

## Rules

- Preserve strict required checks, review controls and signing rules; this skill does not authorize bypasses or settings changes.
- A PR test job may execute project tests with an unprivileged token. Privileged automation must treat the resulting artifacts as untrusted data.
- Do not describe read-only permissions or a successful lint as runtime security certification.

## Examples

- External fork needs lint/tests: propose pull_request validation with contents: read, no secrets or write scopes; use a separate trusted gate for authorized privileged effects.

## Edge Cases

- A fork run awaits approval: report the pending state and repository approval step.
- An aggregator skips after a failed dependency: make its failure behavior explicit without dropping other required checks.

## References

Load [workflow reference](references/REFERENCE.md) for a minimal fork-safe permission shape and current GitHub security guidance.
