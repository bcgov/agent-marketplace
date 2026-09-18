# Phase 6 cleanup changelog

Status: complete

Phase 6 removes fork-era confusion only after confirming that the remaining
files are needed by the marketplace skeleton, generated catalog, GUI, demos,
validation, or companion workflows.

| Area | Decision | Evidence |
| --- | --- | --- |
| `.github/skills/skill-author` and `skill-validator` | Removed | Replaced by `bcgov-create-extension` and `bcgov-find-extension`; companion tests require the legacy names to be absent. |
| `.github/skills/bcgov-find-extension` and `bcgov-create-extension` | Moved | Published companions now live under `skills/community/`; `.github/skills/` is reserved for ignored local-only skills. |
| Flat `skills/<name>/` packages | Remove from supported surface | `scripts/marketplace.py` and `scripts/validate_skill.py` only discover canonical `community` and `security` paths. |
| Root catalog and generated website projections | Keep and regenerate | `make generate` and `make docs` are required by validation, GUI browsing, and demos. |
| `scripts/marketplace.py`, `find_extension.py`, `create_extension.py`, `rescan_candidate.py` | Keep | They implement validation, discovery, authoring, and federated candidate intake used by the MVP. |
| `docs/demos/` walkthroughs | Move to `AI-security/projects/marketplace/` | Phase 5 demos are consumer-facing workflows for the security project; scanner fixtures remain in the marketplace checkout for automated tests. |
| `.mcp.json` | Keep | Repository-level codegraph authoring configuration uses a command lookup and does not affect marketplace publication or distribution. |
| `.vscode/mcp.json` | Remove | Tracked editor configuration hard-coded `/Users/lkraak/Repos/ai-marketplace`; it is machine-specific and unused by validation, catalog generation, GUI, demos, or marketplace workflows. |
| Working specifications | Keep, update stale names | They are the source material for the marketplace implementation; provisional companion names must match the shipped `bcgov-create-extension` package. |
| Pull request template package path | Updated | The template now points reviewers at canonical `skills/<bucket>/<name>/SKILL.md` paths instead of the legacy flat layout. |
| Generated website pages | Keep regenerated | Root `docs/*.html` and `docs/assets/search-index.json` are generated outputs required by Pages and drift checks. |

No package, workflow, or documentation path in the current inventory publishes
hooks, MCP servers, custom agents, or automatic execution. Those references
describe deferred boundaries or security guidance and are not fork artifacts.

## Acceptance check

- [x] Tracked fork-era and legacy surfaces were inventoried and classified.
- [x] Obsolete companion names and flat-package examples were removed or
  explicitly retained only in tests and boundary documentation.
- [x] Generated catalog and website projections were regenerated from source.
- [x] `make verify` passes after cleanup.
- [x] Every removal and retained exception has an evidence-based rationale above.
