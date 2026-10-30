# How to use the BC Gov Agent Marketplace

This is a how-to guide for common tasks in the marketplace. It is written as a recipe set rather than a conceptual overview.

## Find a reviewed extension

1. Open the catalog or use the `bcgov-find-extension` companion.
2. Search by task, use case, or extension type.
3. Inspect the exact record and confirm the source repository and revision.
4. Check the package digest, capabilities, and review result.
5. Confirm the installation only when the record matches the task and the evidence is clear.

If the result is not present in the catalog, the issue is not automatically treated as approved. The workflow may register a candidate, but that remains separate from a reviewed record.

## Install a published extension safely

Use the catalog release tag from the published catalog's `version` field. The installer lock records the exact commit and package digest resolved from that tag. Do not use a checkout whose `release-state` is `development` as an install source.

Preferred flow:

```bash
RELEASE_TAG="catalog-YYYY.MM.DD"

apm install \
  "bcgov/agent-marketplace/skills/community/<skill-name>#${RELEASE_TAG}" \
  --target copilot
```

Fallback flow:

```bash
RELEASE_TAG="catalog-YYYY.MM.DD"
INSTALLER_VERSION="X.Y.Z"

npx skills@"${INSTALLER_VERSION}" add \
  "https://github.com/bcgov/agent-marketplace/tree/${RELEASE_TAG}" \
  --skill "<skill-name>" \
  --agent github-copilot -y
```

Do not treat the catalog as a broad trust signal for arbitrary packages. The signed, immutable revision and the matching review evidence are what establish the trust boundary.

## Create a new extension package

Use the companion creator workflow when you want to turn an idea into a package or a draft PR.

1. Describe the workflow and expected outcome.
2. Search for an equivalent in the marketplace or approved discovery sources.
3. If there is no equivalent, create the package candidate.
4. Review the generated metadata and public output preview.
5. Confirm the draft before it is submitted.

The creator flow is intentionally conservative: it produces a signed draft PR only after explicit confirmation, and it does not bypass repository validation.

## Prepare a draft PR for a new skill or extension

A review-ready PR should include:

- the upstream search evidence and the BC Gov-specific gap;
- source provenance and license information;
- public file inventory and semantic changes;
- declared capabilities and detected policy findings;
- generated catalog changes;
- the exact signed head revision.

The repository validation gate checks package shape, metadata, deterministic policy, generated output, and docs without executing contributed package scripts.

## Handle a federated candidate

If a package is not in the hosted catalog but is identified from a trusted source, the candidate intake path still requires independent scanning and review.

The candidate workflow:

1. identifies the approved discovery source;
2. records the canonical repository, full commit SHA, and path;
3. independently downloads and scans the immutable bytes;
4. compares the supplied digest when one is provided;
5. blocks on a mismatch or a blocking policy finding.

Review remains human-led. A candidate is not treated as approved simply because it was referenced.

## Quarantine, remove, or roll back a published record

Marketplace owners can adjust lifecycle state when a record needs corrective action.

Common actions:

- quarantine the record when a risk or issue requires temporary removal from default discovery;
- remove the record when it must no longer be publicly usable;
- roll back to the last reviewed immutable revision when a newer release is no longer acceptable.

Any rollback or quarantine action must preserve the exact evidence trail and avoid reusing old evidence for changed bytes.

## A practical note on extension types

The current catalog and repo conventions are strongly shaped by `skills/` packages, but the platform’s broader design is not limited to one extension category. The repo’s metadata model, approval flow, and trust controls are defined at the marketplace level, and skills are the current public implementation rather than the only extension kind the architecture is intended to support over time.
