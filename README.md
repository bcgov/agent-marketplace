[![Publish](https://github.com/bcgov/agent-marketplace/actions/workflows/publish.yml/badge.svg)](https://github.com/bcgov/agent-marketplace/actions/workflows/publish.yml)

# BC Gov Agent Marketplace

A public, GitHub-backed marketplace for BC Gov agent assets: skills, prompts, instructions, and agent definitions. Packages have closed metadata, immutable source identity, deterministic package digests, declared capabilities, policy results, and GitHub-native review evidence.

The canonical repository is `bcgov/agent-marketplace` (renamed after this checkout was created).

## Start here

The generated website is under [docs/](docs/). This repository includes two repo-local GitHub Copilot marketplace workflows:

- `bcgov-find-extension` searches reviewed records, shows extension evidence, and requires confirmation before providing installation guidance.
- `bcgov-create-extension` turns an idea or explicitly selected files into a complete package, analyzes and previews public output, then creates a signed draft pull request after one confirmation.

The current config uses `release-state: development`. After this implementation is merged, update [config/marketplace.yaml](config/marketplace.yaml) and the two companion release constants/pages to the first immutable `agent-marketplace` commit, regenerate, and change the state to `published`.

## Repository contract

The repository follows the canonical marketplace skeleton, with a catch-all
`community` bucket and the active `security` specialty. Each supported asset
type has its own package directory and canonical content file.

```text
schemas/                                            closed marketplace metadata schema
config/marketplace.yaml                             centrally controlled release and source policy
skills/<bucket>/<name>/SKILL.md                     portable Agent Skill
prompts/<bucket>/<name>/prompt.prompt.md            reusable prompt
instructions/<bucket>/<name>/instructions.instructions.md  persistent guidance
agents/<bucket>/<name>/agent.agent.md               focused agent definition
<type>/<bucket>/<name>/bcgov-extension.yaml         author-controlled package metadata
scripts/marketplace.py                              validation, scanning, digesting, generation
https://bcgov.github.io/agent-marketplace/assets/catalog.json   live Catalogue (built in CI)
docs/_generated/                                   escaped generated website projection
```

No legacy compatibility contract is promised. A flat `<type>/<name>/...`
layout is not a supported interface, and repo moves or reorgs may change
canonical package paths. Hosted packages use Apache-2.0 and stable IDs of the
form `bcgov-public/<name>`. Authors cannot set review fields. Hooks, MCP
servers, silent automatic execution, and automatic import of non-skill assets
are outside this MVP. GitHub `bcgov` organization membership is the contributor
eligibility proxy; it is not employment verification.

## Local verification

Marketplace users do not need Python, `uv`, or a repository checkout. APM is
preferred for installing published skills, with a catalog-pinned `npx skills`
fallback. Prompts, instructions, and agent definitions use explicit,
harness-specific manual import guidance. Repository maintainers need Python
3.12+, [uv](https://docs.astral.sh/uv/), and Node.js for validation, generation,
and documentation builds.

```bash
make setup
make verify
```

`make verify` checks formatting, lint, unit tests, every portable skill, marketplace metadata and policy, isolated Catalogue/site builds, CODEOWNERS drift, Getting Started command pins, and the static site. Validation treats contributed scripts as data and never executes them.

Regenerate catalog projections after a package or release change:

```bash
make generate
make docs
```

## Previewing the website locally

`make docs` writes the site into [docs/](docs/) but does not serve it. Open the
built pages over HTTP rather than from disk: the catalog page fetches
`assets/catalog.json` and the search index at runtime, and browsers block those
requests on `file://` URLs, so a directly opened page loads with an empty
catalog.

```bash
make generate   # refresh catalog projections if packages or the release changed
make docs       # assemble the pages and search index
make serve      # http://localhost:8000/ — Ctrl+C to stop
```

## Documentation map

The authoritative repository documents are intentionally small and explicit:

- [README.md](README.md) — repo overview, release state, installation and validation commands, and the local workflow.
- [CONTRIBUTING.md](CONTRIBUTING.md) — contributor workflow, package authoring requirements, and PR expectations.
- [spec/ASSET_SPEC.md](spec/ASSET_SPEC.md) — package contracts for the four supported asset types.
- [spec/SKILL_SPEC.md](spec/SKILL_SPEC.md) — additional requirements for `SKILL.md` files.
- [GLOSSARY.md](GLOSSARY.md) — agreed marketplace terms and trust labels.
- [config/marketplace.yaml](config/marketplace.yaml) — release metadata and approved discovery sources.
- [docs/MARKETPLACE_RUNBOOK.md](docs/MARKETPLACE_RUNBOOK.md) — release, quarantine, removal, rollback, and incident-response operations.
- [SECURITY.md](SECURITY.md) — the private vulnerability reporting route.
- [docs/README.md](docs/README.md) — the generated static-site workflow and build caveats.
- [docs/what-is-the-agent-marketplace.md](docs/what-is-the-agent-marketplace.md) — overview of supported asset types, trust evidence, and contributor eligibility.
- [docs/getting-started.md](docs/getting-started.md) — tutorial for a first successful discovery and installation flow.
- [docs/how-to-use-the-marketplace.md](docs/how-to-use-the-marketplace.md) — how-to recipes for common operational tasks.
- [docs/marketplace-reference.md](docs/marketplace-reference.md) — technical reference for repo structure, lifecycle, trust model, and validation mechanics.
- [docs/_pages/](docs/_pages/) and [docs/_partials/](docs/_partials/) — source pages and shared chrome for the static website.

The checked-in repo does not include a companion `projects/marketplace/` tree. This marketplace checkout keeps the source contract, validation fixtures, and generated publication artifacts needed for repository operations and CI, while consumer-facing walkthroughs live outside this checkout.

Pass `PORT` when 8000 is taken, for example `make serve PORT=8080`. The server
reads whatever is already built, so after editing anything in `docs/_pages/`,
`docs/_partials/`, or a package, re-run `make generate && make docs` and reload
the page. Nothing in `docs/*.html` or `docs/_generated/` should be edited by
hand; CI builds those outputs in an isolated directory. CODEOWNERS retains its drift check.

## Trust and operations

- **Approved discovery source** means the source may be searched; individual results are not approved.
- **Unreviewed candidate** means trusted CI scanning and BC Gov human review are still pending for the immutable source.
- **Marketplace reviewed** means named reviewers assessed the exact published revision and digest.

Do not describe packages as safe or verified secure. See [SECURITY.md](SECURITY.md), [docs/MARKETPLACE_DECISIONS.md](docs/MARKETPLACE_DECISIONS.md), and [docs/MARKETPLACE_RUNBOOK.md](docs/MARKETPLACE_RUNBOOK.md).
