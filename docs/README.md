# Marketplace website

The static site for [`bcgov/agent-marketplace`](https://github.com/bcgov/agent-marketplace). A portable Bash wrapper invokes dependency-free Node.js page assembly and search indexing.

This directory contains the published website and the source files that generate it. For repository-level rules, contributor workflow, and operational guidance, see [../README.md](../README.md), [../CONTRIBUTING.md](../CONTRIBUTING.md), [../docs/MARKETPLACE_RUNBOOK.md](MARKETPLACE_RUNBOOK.md), and [../spec/SKILL_SPEC.md](../spec/SKILL_SPEC.md).

The deeper Diátaxis documentation sits alongside the generated site and follows a progressive-disclosure flow:

- [what-is-the-agent-marketplace.md](what-is-the-agent-marketplace.md) — explains the marketplace, its trust model, and the broader extension vision.
- [getting-started.md](getting-started.md) — a tutorial for a first successful use of the catalog and companion workflows.
- [how-to-use-the-marketplace.md](how-to-use-the-marketplace.md) — task-oriented how-to guidance for common workflows.
- [marketplace-reference.md](marketplace-reference.md) — a technical reference for repo structure, lifecycle, validation, and security controls.

```bash
make generate
make docs
```

Edit source pages under `_pages/` and shared chrome under `_partials/`. Do not hand-edit root HTML outputs or `_generated/catalog-cards.html`; `scripts/marketplace.py` generates catalog projections from closed package metadata.

`build.sh` invokes `build-pages.js` to insert generated cards and assemble pages, then `generate-search-index.js` assigns heading anchors and writes `assets/search-index.json`. CI validates source and builds in an isolated directory (`bash docs/build.sh /tmp/site/docs`). The single `publish.yml` workflow stages the site around the exact release asset at `assets/catalog.json`. Generated Catalogue, root HTML, search index and cards are ignored. Authored pages/configuration and CODEOWNERS stay tracked. See [publication.md](publication.md) for controls and recovery.

Phase 6 cleanup decisions are tracked in [CLEANUP_CHANGELOG.md](CLEANUP_CHANGELOG.md).
