# BC Gov Agent Marketplace

A public, GitHub-backed marketplace for reviewed BC Gov Agent Skills. Packages have closed metadata, immutable source identity, deterministic package digests, declared capabilities, policy results, and GitHub-native review evidence.

The canonical repository is `bcgov/agent-marketplace` (renamed after this checkout was created).

## Start here

The generated website is under [docs/](docs/). This repository includes two repo-local GitHub Copilot marketplace workflows:

- `bcgov-find-extension` searches reviewed records, shows extension evidence, and requires confirmation before providing installation guidance.
- `bcgov-create-extension` turns an idea or explicitly selected files into a complete package, analyzes and previews public output, then creates a signed draft pull request after one confirmation.

The current config uses `release-state: development`. After this implementation is merged, update [config/marketplace.yaml](config/marketplace.yaml) and the two companion release constants/pages to the first immutable `agent-marketplace` commit, regenerate, and change the state to `published`.

## Repository contract

The repository follows the canonical marketplace skeleton, with the catch-all `community` bucket for non-specialized skills and the active specialty limited to `security`.

```text
schemas/                                            closed marketplace metadata schema
config/marketplace.yaml                             centrally controlled release and source policy
skills/<bucket>/<name>/SKILL.md                     portable Agent Skill instructions
skills/<bucket>/<name>/bcgov-extension.yaml         author-controlled package metadata
skills/community/                                   catch-all bucket for non-specialized skills
skills/security/                                    active Phase 1 specialty inventory
scripts/marketplace.py                              validation, scanning, digesting, generation
catalog/catalog.json                                generated machine-readable catalog
docs/_generated/                                   escaped generated website projection
```

No legacy compatibility contract is promised. A flat `skills/<name>/...` layout is not a supported interface, and repo moves or reorgs are allowed to break legacy paths when they are replaced by the canonical `community` or `security` structure. Hosted packages use Apache-2.0 and stable IDs of the form `bcgov-public/<name>`. Authors cannot set review fields. Hooks, MCP servers, custom agents, and automatic execution are outside this MVP.

## Local verification

Marketplace users do not need Python, `uv`, or a repository checkout. APM is
preferred for installing published skills, with a catalog-pinned `npx skills`
fallback. Repository maintainers need Python 3.12+, [uv](https://docs.astral.sh/uv/),
and Node.js for validation, generation, and documentation builds.

```bash
make setup
make verify
```

`make verify` checks formatting, lint, unit tests, every portable skill, marketplace metadata and policy, generated-output drift, Getting Started command pins, and the static site. Validation treats contributed scripts as data and never executes them.

Regenerate catalog projections after a package or release change:

```bash
make generate
make docs
```

## Trust and operations

- **Approved discovery source** means the source may be searched; individual results are not approved.
- **Unreviewed candidate** means trusted CI scanning and BC Gov human review are still pending for the immutable source.
- **Marketplace reviewed** means named reviewers assessed the exact published revision and digest.

Do not describe packages as safe or verified secure. See [SECURITY.md](SECURITY.md), [docs/MARKETPLACE_DECISIONS.md](docs/MARKETPLACE_DECISIONS.md), and [docs/MARKETPLACE_RUNBOOK.md](docs/MARKETPLACE_RUNBOOK.md).
