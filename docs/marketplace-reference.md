# Marketplace reference

This is the reference document for the repository and the marketplace mechanics. It is organized around the actual contracts and operational boundaries of this codebase.

## Repository layout

```text
config/marketplace.yaml               centrally controlled release and source policy
schemas/                              marketplace metadata schemas
skills/<bucket>/<name>/SKILL.md      portable instruction manifest
skills/<bucket>/<name>/bcgov-extension.yaml  author-controlled package metadata
scripts/marketplace.py                validation, scanning, digesting, and generation
catalog/catalog.json                 generated machine-readable catalog
docs/                                public website source and generated pages
spec/SKILL_SPEC.md                   authoritative skill specification
```

## Supported extension types

This repository is an agent extension marketplace rather than a skill-only registry.

The public MVP is intentionally narrow and currently validates skills as the primary published extension type. However, the extension taxonomy, discovery sources, and approval pipeline are not hard-wired to one file format alone. The general marketplace model can support prompt, instruction, agent, and skill entries, while the current catalog remains conservative and intentionally focused on the skill surface that the repo can validate and review reliably.

In practical terms:

- skills are the current reviewed and published default;
- the marketplace architecture is wider than the current public catalog;
- future extension forms should still satisfy the same trust, provenance, and review controls before publication.

## Lifecycle and review model

Each package lives under a review and lifecycle model:

- `active` — available through default discovery;
- `quarantined` — removed from default discovery while risk is assessed;
- `removed` — intentionally retired from the public catalog;
- `draft` or unpublished states — used before a reviewed record is published.

Review is attached to the exact immutable source revision. Changed bytes invalidate prior review evidence.

## Trust properties

The marketplace minimizes trust assumptions by requiring:

- immutable source identity;
- deterministic packaging and digesting;
- explicit capability declaration;
- policy findings from reviewed validation;
- signed repository-backed workflows;
- human approval on the exact published revision.

It does not assume that a record is safe because it is public or because it came from a trusted authoring source alone.

## Validation and generation

The repository validation path treats contributed package files as data and does not execute them. It checks:

- layout and naming;
- metadata schema requirements;
- policy and scanner findings;
- generated output parity;
- docs and public site drift;
- the canonical repo state for the published release.

The `make verify` command is the repository’s launch gate.

## Commands used by maintainers

```bash
make setup
make generate
make verify
make docs
make serve
```

This is the operational baseline for maintainers and reviewers. The same validation flow is used to confirm that the catalog, metadata, and public docs are still in agreement.

## Security and operations

Marketplace owners and reviewers should use the repository’s formal reporting and runbook paths, including:

- the private security advisory route;
- the operations runbook for quarantine, recovery, and rollback;
- the source-controlled publication flow for exact-review release changes.

## Quick summary

The marketplace is a repository-backed, evidence-first discovery layer for trusted agent extensions. Skills are the first publicly active implementation, but the design scope is broader than a skill-only registry and the trust model is intentionally shaped to support additional extension types under the same governance model.
