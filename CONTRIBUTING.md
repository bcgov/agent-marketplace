# Contributing to the BC Gov Agent Marketplace

Contributions use signed commits on branches in `bcgov/agent-marketplace`. The author must be a member of the GitHub `bcgov` organization; this is an eligibility proxy, not employment verification. The eligibility workflow fails closed when it cannot confirm membership. See the [intake policy](docs/COMMUNITY_INTAKE_POLICY.md) for token requirements and troubleshooting. Fork pull requests fail closed. If you lack branch access, keep your staged package and request access through a repository issue.

## Preferred authoring path

From any workspace with the installed companion, ask Copilot:

> Turn this workflow idea into a BC Gov agent asset and prepare a draft pull request.

The companion searches for equivalents, creates the package in isolated staging, inventories capabilities, inspects public output, shows one complete preview, and submits a signed draft PR only after confirmation. It fetches the hosted contracts and relies on protected-branch CI for authoritative validation, so contributors do not need a marketplace checkout, Python, or `uv`. It cannot approve or merge its own work.

## Package requirements

Every hosted package has a type-specific content file and the common
`bcgov-extension.yaml` manifest:

```text
skills/<bucket>/<name>/SKILL.md
prompts/<bucket>/<name>/prompt.prompt.md
instructions/<bucket>/<name>/instructions.instructions.md
agents/<bucket>/<name>/agent.agent.md
<type>/<bucket>/<name>/bcgov-extension.yaml
```

See [spec/ASSET_SPEC.md](spec/ASSET_SPEC.md) for all package formats and
[spec/SKILL_SPEC.md](spec/SKILL_SPEC.md) for the additional skill contract.
Skills may include optional flat resource directories:

```text
skills/<bucket>/<name>/
├── SKILL.md
├── bcgov-extension.yaml
├── scripts/       optional, flat files only
├── references/    optional, flat files only
└── assets/        optional, flat files only
```

All package manifests follow [schemas/bcgov-extension-v1alpha1.schema.json](schemas/bcgov-extension-v1alpha1.schema.json), use IDs of the form `bcgov-public/<name>`, declare capabilities, and use Apache-2.0. Authors must not add review fields.

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

Specialty owners are declared in `config/specialties.yaml`, not in
`config/marketplace.yaml`. To onboard a Specialty, submit an admin-reviewed PR
adding its id, display name, owner team, description, `owning-team` review rule
and display flair, then run `make generate` to commit the updated
`.github/CODEOWNERS`. The type-first package paths receive only that team's
ownership. A single-member team is permitted; if its sole member authors a
change to owned paths, an admin may use the PR-only review bypass after recording
the author, sole ownership, and merging admin on the PR. Admins also check with
the current owner before changing an existing team's owner or review rule.
Security alone owns `config/security-policy.yaml` and `tests/security-policy/`.
Policy blocking-rule additions need corresponding blocking and benign tests.

## Federated candidates

Third-party candidates use the issue intake path, not a branch. They must identify an approved discovery source, canonical HTTPS GitHub repository, full commit SHA, package path, and capability evidence. An expected digest is optional. Trusted CI fetches the immutable bytes, computes the package-tree digest, and scans them without execution; a supplied digest mismatch or blocking finding fails closed.

See [docs/MARKETPLACE_RUNBOOK.md](docs/MARKETPLACE_RUNBOOK.md) for publication, quarantine, removal, and rollback.
