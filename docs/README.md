# Marketplace website

The static site for [`bcgov/agent-marketplace`](https://github.com/bcgov/agent-marketplace). A portable Bash wrapper invokes dependency-free Node.js page assembly and search indexing.

This directory contains the published website and the source files that generate it. For repository-level rules, contributor workflow, and operational guidance, see [../README.md](../README.md), [../CONTRIBUTING.md](../CONTRIBUTING.md), [../docs/MARKETPLACE_RUNBOOK.md](MARKETPLACE_RUNBOOK.md), and [../spec/SKILL_SPEC.md](../spec/SKILL_SPEC.md).

```bash
make generate
make docs
```

Edit source pages under `_pages/` and shared chrome under `_partials/`. Do not hand-edit root HTML outputs or `_generated/catalog-cards.html`; `scripts/marketplace.py` generates catalog projections from closed package metadata.

`build.sh` invokes `build-pages.js` to insert generated cards and assemble pages, then `generate-search-index.js` assigns heading anchors and writes `assets/search-index.json`. CI rebuilds and rejects drift. GitHub Pages publishes the complete `docs/` directory, including `assets/catalog.json` for machine-readable discovery.

Phase 6 cleanup decisions are tracked in [CLEANUP_CHANGELOG.md](CLEANUP_CHANGELOG.md).
