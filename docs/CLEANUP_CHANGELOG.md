# Phase 6 cleanup changelog

Status: initial cleanup pass complete

Phase 6 removes fork-era confusion only after confirming that the remaining
files are needed by the marketplace skeleton, generated catalog, GUI, demos,
validation, or companion workflows.

| Area | Decision | Evidence |
| --- | --- | --- |
| `.github/skills/skill-author` and `skill-validator` | Removed | Replaced by `bcgov-create-extension` and `bcgov-find-extension`; companion tests require the legacy names to be absent. |
| Flat `skills/<name>/` packages | Remove from supported surface | `scripts/marketplace.py` and `scripts/validate_skill.py` only discover canonical `community` and `security` paths. |
| Root catalog and generated website projections | Keep and regenerate | `make generate` and `make docs` are required by validation, GUI browsing, and demos. |
| `scripts/marketplace.py`, `find_extension.py`, `create_extension.py`, `rescan_candidate.py` | Keep | They implement validation, discovery, authoring, and federated candidate intake used by the MVP. |
| `docs/demos/` and demo fixtures | Keep | Phase 5 onboarding journeys depend on them; fixtures are scanned as data and never executed. |
| `.mcp.json` and `.vscode/mcp.json` | Keep for now; review separately | These are local codegraph authoring-tool configuration, not marketplace publication or distribution paths. The VS Code path is machine-specific and is a cleanup candidate once the supported developer-tooling contract is decided. |
| Working specifications | Keep, update stale names | They are the source material for the marketplace implementation; provisional companion names must match the shipped `bcgov-create-extension` package. |
| Pull request template package path | Updated | The template now points reviewers at canonical `skills/<bucket>/<name>/SKILL.md` paths instead of the legacy flat layout. |
| Generated website pages | Keep regenerated | Root `docs/*.html` and `docs/assets/search-index.json` are generated outputs required by Pages and drift checks. |

No package, workflow, or documentation path in the current inventory publishes
hooks, MCP servers, custom agents, or automatic execution. Those references
describe deferred boundaries or security guidance and are not fork artifacts.
