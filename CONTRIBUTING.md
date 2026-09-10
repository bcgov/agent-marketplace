# Contributing to the BC Gov Agent Marketplace

Contributions use signed commits on branches in `bcgov/agent-marketplace`. Fork pull requests fail closed. If you lack branch access, keep your staged package and request access through a repository issue.

## Preferred authoring path

From any workspace with the installed companion, ask Copilot:

> Turn this workflow idea into a BC Gov Agent Skill and prepare a draft pull request.

The companion searches for equivalents, creates the package in isolated staging, inventories capabilities, inspects public output, shows one complete preview, and submits a signed draft PR only after confirmation. It fetches the hosted contracts and relies on protected-branch CI for authoritative validation, so contributors do not need a marketplace checkout, Python, or `uv`. It cannot approve or merge its own work.

## Package requirements

Every hosted package contains:

```text
skills/community/<name>/
├── SKILL.md
├── bcgov-extension.yaml
├── scripts/       optional, flat files only
├── references/    optional, flat files only
└── assets/        optional, flat files only
```

`SKILL.md` follows [spec/SKILL_SPEC.md](spec/SKILL_SPEC.md). The companion manifest follows [schemas/bcgov-extension-v1alpha1.schema.json](schemas/bcgov-extension-v1alpha1.schema.json), uses ID `bcgov-public/<name>`, declares every filesystem read/write, network host, command, environment variable, secret name, and data class, and uses Apache-2.0. Authors must not add review fields.

Before authoring, search the BC Gov catalog and all approved discovery sources in [config/marketplace.yaml](config/marketplace.yaml). Prefer upstream contribution when no BC Gov-specific policy or workflow gap exists.

Only include explicitly selected public resources. Never publish credentials, personal information, private endpoints, or sensitive operational data.

## Verify and submit

```bash
make generate
make verify
```

The gate validates package shape, metadata, deterministic security policy, generated catalog parity, command contracts, and docs without executing contributed package scripts.

A review-ready PR includes:

- upstream-search evidence and the BC Gov-specific gap;
- source provenance and license;
- public file inventory and semantic changes;
- structured capabilities and scanner findings;
- generated catalog changes;
- the exact signed head revision.

CODEOWNERS and package maintainers review that exact revision. Changed bytes or capabilities invalidate prior evidence. Human reviewers and protected-branch CI alone decide publication.

## Federated candidates

Third-party candidates use the issue intake path, not a branch. They must identify an approved discovery source, canonical HTTPS GitHub repository, full commit SHA, package path, and capability evidence. An expected digest is optional. Trusted CI fetches the immutable bytes, computes the package-tree digest, and scans them without execution; a supplied digest mismatch or blocking finding fails closed.

See [docs/MARKETPLACE_RUNBOOK.md](docs/MARKETPLACE_RUNBOOK.md) for publication, quarantine, removal, and rollback.
