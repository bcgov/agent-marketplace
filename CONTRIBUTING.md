# Contributing to the BC Gov Agent Marketplace

Contribute through a fork branch, a repository branch, or the creation companion.
Commits must meet the repository's signing requirements. Public `bcgov` GitHub
membership is required for Community automatic eligibility; this is an
eligibility proxy, not employment verification. Unconfirmed membership produces
a human-review hold, while format and security errors still require fixes.
Preview results do not prove production activation or live rulesets.

## Browser contribution

Use the [Contribute page](https://bcgov.github.io/agent-marketplace/contribute.html)
to select the type, Community or a registered Specialty, stable name, your
maintainer username, and summary. No local commands are required.

1. Open the native-file prefill and edit its body. Without upstream write access,
   create/select a fork and a contribution branch. Commit/propose that file and
   record the actual fork repository and branch. Do not open the PR yet.
2. On that **same fork and existing branch**, use Add file -> Create new file
   to add the matching `bcgov-extension.yaml` beside the native file. The page
   supplies the exact path, a second prefill and a copyable minimal Manifest.
   Declare your individual maintainer and actual capabilities; `none` means no
   declared access. Commit directly to the existing branch.
3. Open one upstream PR from that branch. Confirm the intended base branch and
   both matching paths in Files changed. Use the single type-neutral template.
   For a Specialty, mark ready for review to request the owners declared by the
   **base branch's** CODEOWNERS; drafts do not request owners automatically.
4. Read exact-head check details. Fix hard failures on the same branch. A passing
   `human-review` route is a review hold. If fork runs await approval, ask a
   maintainer to approve the existing workflow run. Missing checks are pending
   evidence. Automation being off does not waive required checks.

If summary validation fails, add native frontmatter `description:` or Manifest
`summary:`; native-format requirements still apply. If the Manifest is missing,
add it beside the native file on the existing branch. Quote YAML values that
contain special punctuation. If membership cannot be confirmed, make your
organization membership public when appropriate or request a maintainer's
review of the hold. Never share tokens or credentials.

GitHub signs web-interface commits. Inspect each PR commit's **Verified** status.
For unsigned local commits, configure Git's supported signing method and recreate
the affected commits with signing enabled on the head branch; coordinate with
maintainers before rewriting a shared branch. Check the replacement commits'
Verified status before requesting review. Do not disable signature requirements.

## Preferred authoring path

From any workspace with the installed companion, ask Copilot:

> Turn this workflow idea into a BC Gov agent asset and prepare a draft pull request.

The companion searches for equivalents, creates the package in isolated staging, inventories capabilities, inspects public output, shows one complete preview, and submits a signed draft PR only after confirmation. It fetches the hosted contracts and relies on protected-branch CI for authoritative validation, so contributors do not need a marketplace checkout, Python, or `uv`. It cannot approve or merge its own work.

## Package requirements

Every hosted package has a type-specific content file and the common
`bcgov-extension.yaml` manifest:

```text
skills/<bucket>/<name>/SKILL.md
prompts/<bucket>/<name>/<name>.prompt.md
instructions/<bucket>/<name>/<name>.instructions.md
agents/<bucket>/<name>/<name>.agent.md
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

All package manifests follow [schemas/bcgov-extension-v1alpha1.schema.json](schemas/bcgov-extension-v1alpha1.schema.json).
Only `maintainers` and `capabilities` are mandatory authored governance fields.
IDs are derived as `bcgov-public/<type>/<name>`, unique per type across all
Specialties, including retained removed records. Type/name stays stable through
reviewed Specialty transfers. Effective summary is required and can come from
native `description:` or a Manifest override. Other metadata uses validated
defaults, including Apache-2.0. Authors must not add review fields.

Before authoring, search the BC Gov catalog and all approved discovery sources in [config/marketplace.yaml](config/marketplace.yaml). Prefer upstream contribution when no BC Gov-specific policy or workflow gap exists.

Only include explicitly selected public resources. Never publish credentials, personal information, private endpoints, or sensitive operational data.

## Verify and submit from a local checkout

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
