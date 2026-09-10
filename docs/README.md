# Marketplace website

The static site for [`bcgov/agent-marketplace`](https://github.com/bcgov/agent-marketplace). A portable Bash wrapper invokes dependency-free Node.js page assembly and search indexing.

```bash
make generate
make docs
```

Edit source pages under `_pages/` and shared chrome under `_partials/`. Do not hand-edit root HTML outputs or `_generated/catalog-cards.html`; `scripts/marketplace.py` generates catalog projections from closed package metadata.

`build.sh` invokes `build-pages.js` to insert generated cards and assemble pages, then `generate-search-index.js` assigns heading anchors and writes `assets/search-index.json`. CI rebuilds and rejects drift. GitHub Pages publishes the complete `docs/` directory, including `assets/catalog.json` for machine-readable discovery.
