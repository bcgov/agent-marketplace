# Codex patch inventory — issue #9

**Question (issue #9):** What does the Codex patch (`working/agent-marketplace-changes.patch`, plus `working/APPLY-CHANGES.txt`) add or change compared with the baseline working tree, grouped by area, with a lean-v1 verdict per idea?

## Method and primary sources

- Patch: `working/agent-marketplace-changes.patch` — 85 files, unified diff, base commit `246f032d1b99d594834e16e1654a37eb2c09ef56` (as recorded in the handoff notes). **Never applied** — it does not apply cleanly to current `main`; read as plain text only (`grep -n '^diff --git'` to map file→line ranges, then `view` with `view_range`).
- Notes: `working/APPLY-CHANGES.txt` — handoff notes confirming no branch/PR/release was ever created from the patch, and that it should be applied to a clean clone by someone else rather than merged directly.
- Baseline: the actual uncommitted working tree at `/Users/lkraak/Repos/ai-marketplace` (current `main`, not just `HEAD` — i.e., including anything already present on disk). Baseline has evolved substantially past the patch's `246f032` base, so many ideas the patch "adds" already exist in baseline in equivalent, partial, or more advanced form; each idea below was checked against the live file content, not assumed absent.
- Issue: `gh issue view 9 --repo bcgov/agent-marketplace` — question text, parent #7, blocking #19, label `wayfinder:research`.

**Lean v1 scope used for all verdicts:**
- Extension types in scope: **skill, instructions, prompt, agent only.** Hooks, MCP, and plugins are explicitly **out of scope** for v1 and are flagged only briefly below wherever the patch touches them.
- Contribution/publication model: **community extensions auto-publish after passing deterministic scans; specialty (team-owned) extensions require team review; contribution happens via a companion skill, a PR, or the GitHub web UI.**

**Verdict legend:** `want` = clearly valuable and compatible with lean v1; `maybe` = plausible but secondary, conditional, or scope-dependent; `skip` = conflicts with lean v1 scope/model or is not worth the cost now.

Patch locations cite file names and, where useful, patch-file line ranges. Baseline comparisons refer to the current uncommitted file contents, not merely the last commit. Sections that overlap (for example CI and scanning, or companion skills and tests) cross-reference one another.

---

## 1. Workflows / CI security

Patch files: `.github/CODEOWNERS` (patch:1-38), `.github/ISSUE_TEMPLATE/extension-problem.yml` (39-77), `.github/ISSUE_TEMPLATE/extension-request.yml` (78-135), `.github/pull_request_template.md` (136-188), `.github/workflows/community-intake.yml` (189-386, shape only here — see §3 for scan semantics), `.github/workflows/dependabot-auto-merge.yml` (387-435), `.github/workflows/federated-candidate.yml` (436-514, shape only), `.github/workflows/pr.yml` (603-813), `Makefile` (1154-1173).

Baseline already has a mature `.github/` (not visible in a depth-2 listing because it's a dotdir): `CODEOWNERS`, `ISSUE_TEMPLATE/federated-candidate.yml`, `pull_request_template.md`, and `workflows/{community-intake,dependabot-auto-merge,federated-candidate,pages,pr,release}.yml` — all pre-dating or superseding the patch's base state.

1. **Require maintainer/CODEOWNER approval for community namespaces**
   - Patch: `.github/CODEOWNERS:1-38`.
   - Baseline: **No.** Baseline deliberately leaves community paths ownerless so they can auto-publish on the intake gate (`.github/CODEOWNERS:5-13`); specialty paths require owners (`:15-26`).
   - Verdict: **skip** — directly contradicts the lean-v1 auto-publish-for-community model.

2. **Add `/plugins/community/` and `/plugins/security/` CODEOWNERS entries**
   - Patch: `.github/CODEOWNERS:13-26`.
   - Baseline: **No** — only skills/prompts/instructions/agents/hooks/mcp are covered (`.github/CODEOWNERS:5-26`), no plugins.
   - Verdict: **skip** — plugins are out of v1 scope.

3. **Add a public "extension problem/compatibility" issue template**
   - Patch: `.github/ISSUE_TEMPLATE/extension-problem.yml:39-77`.
   - Baseline: **No** — only `federated-candidate.yml` exists for registering third-party skills (`.github/ISSUE_TEMPLATE/federated-candidate.yml:1-52`).
   - Verdict: **maybe** — reasonable contribution/support-intake surface for skill/instructions/prompt/agent, narrow it to v1 types.

4. **Add a generalized "extension request" issue template**
   - Patch: `.github/ISSUE_TEMPLATE/extension-request.yml:78-135`.
   - Baseline: **No** equivalent beyond `federated-candidate.yml`.
   - Verdict: **maybe** — a GitHub-web contribution path fits the model, but strip Hook/MCP/Plugin options for v1.

5. **Require capability/access declarations in extension requests**
   - Patch: `.github/ISSUE_TEMPLATE/extension-request.yml:101-135`.
   - Baseline: **Partial** — federated-candidate template already requires filesystem/network/command/env/secret/data-class capability declarations (`.github/ISSUE_TEMPLATE/federated-candidate.yml:38-46`); ordinary requests have no equivalent.
   - Verdict: **want** — needed for deterministic screening of v1 types.

6. **Generalize the PR template from skill-only to outcome/provenance/behavior/review-evidence**
   - Patch: `.github/pull_request_template.md:136-188`.
   - Baseline: **No** — baseline PR template is skill-specific (`SKILL.md`, skill-spec checklist) (`.github/pull_request_template.md:1-33`).
   - Verdict: **want** — matches skill/instructions/prompt/agent contribution via PR.

7. **Add explicit capability/access/recovery/validation/immutable-evidence checklist items**
   - Patch: `.github/pull_request_template.md:145-185`.
   - Baseline: **Partial** — baseline already asks for capability/review evidence, `make verify`, no-secrets, and exact head/digest review (`.github/pull_request_template.md:20-31`), but lacks access/recovery framing and generated-projection fields.
   - Verdict: **want** — strengthens scanning/team-review without new scope.

8. **Replace author-trust/velocity auto-publish gate in `community-intake.yml` with a "trusted-base scanner"**
   - Patch: `.github/workflows/community-intake.yml:189-386`.
   - Baseline: **No** — baseline resolves org membership, account age, open-PR velocity, then calls `marketplace.py intake` (`.github/workflows/community-intake.yml:1-149`).
   - Verdict: **maybe** — the scanning shape is good, but it would remove baseline's existing author-abuse controls (see §3 for the policy-level conflict).

9. **Scan all PR changes (not just manifests) using separate trusted-policy vs. candidate checkouts**
   - Patch: `.github/workflows/community-intake.yml:189-245`.
   - Baseline: **No** — baseline operates from a single checkout and only inspects changed community manifest paths (`:13-48`).
   - Verdict: **want** — running trusted policy against untrusted candidate-as-data is a strong security shape.

10. **Remove workflow write permissions; keep scan evidence as an uploaded artifact**
    - Patch: `.github/workflows/community-intake.yml:189-245` (`permissions: {}` + artifact upload).
    - Baseline: **No** — baseline grants `issues: read`/`pull-requests: write` and labels PRs `community-intake:hold` (`:16-28, 111-149`), no evidence artifact.
    - Verdict: **want** — least privilege + auditable evidence.

11. **Pin actions, freeze dependency execution, add timeouts, disable caches**
    - Patch: `.github/workflows/community-intake.yml:189-245`.
    - Baseline: **Partial** — setup-uv is pinned, but `actions/checkout@v7` is unpinned, no timeout, default uv caching (`:30-45`).
    - Verdict: **want** — standard supply-chain hygiene.

12. **Delete the automatic Dependabot approval/auto-merge workflow**
    - Patch: `.github/workflows/dependabot-auto-merge.yml:387-435` (deletion).
    - Baseline: **Yes, present** — `pull_request_target`, Dependabot-only gate, `contents:write`/`pull-requests:write`, auto-approve + auto-merge (`.github/workflows/dependabot-auto-merge.yml:1-43`).
    - Verdict: **maybe** — safer, but orthogonal to the extension-contribution model; only remove if repo policy wants manual dependency merges.

13. **Split `federated-candidate.yml` into a read-only rescan job and a separate issue-comment job**
    - Patch: `.github/workflows/federated-candidate.yml:436-514`.
    - Baseline: **No** — baseline's single `rescan` job both scans and has `issues: write` (`.github/workflows/federated-candidate.yml:1-39`).
    - Verdict: **want** — separates untrusted-candidate analysis from issue mutation; **maybe** overall since federated candidates aren't the primary v1 contribution path.

14. **Upload/download immutable scan evidence before commenting**
    - Patch: `.github/workflows/federated-candidate.yml:478-514`.
    - Baseline: **No** — baseline writes `candidate-report.md` and comments in the same write-enabled job (`:25-39`).
    - Verdict: **want** — improves provenance.

15. **Pin checkout, disable dependency cache in `federated-candidate.yml`**
    - Patch: `:446-478`.
    - Baseline: **Partial** — setup-uv pinned but `actions/checkout@v7` unpinned, cache enabled (`:20-24`).
    - Verdict: **want**.

16. **`pr.yml`: allow fork PR checks to run instead of a hard-failing fork gate**
    - Patch: `.github/workflows/pr.yml:603-813`.
    - Baseline: **No** — baseline has a `fork-gate` job that fails fork PRs outright, blocking all downstream validation.
    - Verdict: **want** — community contribution via GitHub forks needs this; keep checks secret-free and read-only.

17. **Deny-all workflow permissions with per-job read grants**
    - Patch: `.github/workflows/pr.yml:603-813`.
    - Baseline: **Partial** — workflow-wide `contents: read` only (`:26-28`), no per-job narrowing.
    - Verdict: **want**.

18. **Pin checkout/setup-node, disable caches, freeze uv, add timeouts in `pr.yml`**
    - Baseline: **Partial** — `actions/checkout@v7`/`setup-node@v7` unpinned, uv cache enabled, no timeouts (`:64-80, 91-99`).
    - Verdict: **want**.

19. **Add workflow YAML linting and a browser catalog-UI test step**
    - Baseline: **Partial** — runs Ruff, pytest, marketplace validation, docs-build/drift checks (`:72-80, 108-124`), but no `yamllint` and no `tests/test_catalog_ui.js`.
    - Verdict: **want** — deterministic checks fit the model; catalog-UI testing is adjacent, not extension-specific.

20. **Make the aggregate `results` job fail on any skipped upstream validation**
    - Patch: `.github/workflows/pr.yml:760-813`.
    - Baseline: **Partial** — baseline's aggregator treats skipped jobs as passing (`:126-150`).
    - Verdict: **want** — prevents silent bypass of required checks.

21. **Wire browser catalog tests into `make test` / `make verify`**
    - Patch: `Makefile:1154-1173`.
    - Baseline: **No** — `make test` is `uv run pytest -q` only (`Makefile:25-27`); `make verify` runs Ruff/yamllint/pytest/skill-validate/marketplace-validate/docs-build with no Node step (`:58-72`).
    - Verdict: **maybe** — only if the JS harness (§4/§8) is actually adopted; otherwise skip.

**Out of scope note:** `.mcp.json` (patch:1031-1048) is MCP tooling config; baseline doesn't have this file at all but does document (`docs/CLEANUP_CHANGELOG.md:19-23`) that `.mcp.json` is retained only for local codegraph authoring, unrelated to marketplace publication — not analyzed further (hooks/MCP/plugins out of scope).

---

## 2. Extension types

Patch files: `docs/EXTENSION_TYPES.md` (2300-2351), `schemas/bcgov-extension-v1alpha1.schema.json` (12437-12611), `scripts/create_extension.py` (12612-13189), `scripts/find_extension.py` (13190-13820), `scripts/marketplace.py` (13821-15042, type-taxonomy portions), `docs/_pages/types.html` (3819-3844) + built `docs/types.html` (10594-12362), `tests/test_extension_model.py` (16835-17276, new file).

Baseline today supports **four** declarative types already: skill, prompt, instructions, agent (`spec/ASSET_SPEC.md:3-28`, `scripts/marketplace.py:18-39,219-252`, `GLOSSARY.md:7-28`), with hooks/MCP explicitly deferred (`spec/ASSET_SPEC.md:3-5`) and no plugin concept at all.

1. **Expand taxonomy from 4 to 7 types (add hook, mcp, plugin)**
   - Patch: `schemas/...schema.json:74-91`, `scripts/create_extension.py:20-35,128-157`, `scripts/marketplace.py:24-50,205-234`, `docs/EXTENSION_TYPES.md:1-46`, `docs/_pages/types.html:1-20`, `tests/test_extension_model.py:45-70`.
   - Baseline: **Partial** — 4 types exist; schema has no `type` enum at all yet (`schemas/...schema.json:1-126`); `create_extension.py` scaffolds 4 active types with hook/mcp explicitly rejected (`:19-45`); `find_extension.py` recognizes 6 types but only auto-installs skills and has no `plugin` (`:35-53`).
   - Verdict: **want** the 4-type taxonomy formalization; **skip** hook/mcp/plugin additions — out of v1 scope.

2. **Add explicit manifest `type` field with backward-compatible "untyped = skill" default**
   - Patch: `schemas/...schema.json:74-91,190-211`; `scripts/marketplace.py:218-257`; `tests/test_extension_model.py:96-109`.
   - Baseline: **No** — current schema has no `type` field (`:14-126`); baseline infers type solely from directory (`scripts/marketplace.py:18-39,219-252`).
   - Verdict: **want** — needed for prompt/instructions/agent to be declared explicitly while skills stay backward-compatible.

3. **Add type-specific `entrypoint` metadata with suffix validation**
   - Patch: `schemas/...schema.json:83-89,190-211`; `scripts/marketplace.py:243-280`; `scripts/find_extension.py:274-316`; tests `:84-95`.
   - Baseline: **No** — fixed filenames via `ARTIFACT_FILES`, no manifest entrypoint field (`scripts/marketplace.py:30-39,245-252`).
   - Verdict: **want** for the 4 v1 types; don't generalize to runtime descriptors.

4. **Add declared client `compatibility` + `usage.install`/`usage.uninstall`**
   - Patch: `schemas/...schema.json:90-125,190-211`; `scripts/create_extension.py:168-200`; `docs/EXTENSION_TYPES.md:20-31`; tests `:72-82`.
   - Baseline: **Partial/different** — only has `compatibility.not-ready-on` (`schemas/...schema.json:70-86`, `spec/ASSET_SPEC.md:48-60`); no `usage` field.
   - Verdict: **want**, especially for prompt/instructions/agent activation that is client-specific.

5. **Add `capabilities.tool-scopes` for agents (compare declared tool scopes vs. native `tools`/`allowed-tools`)**
   - Patch: `schemas/...schema.json:151-188`; `scripts/create_extension.py:190-200`; `scripts/marketplace.py:437-481`; tests `:45-70`.
   - Baseline: **No** — capabilities cover filesystem/network/commands/env/secrets/data-class only (`schemas/...schema.json:102-126`).
   - Verdict: **maybe** for agents — keep declarative/non-enforcing framing, don't imply a runtime permission boundary.

6. **Scaffold all 7 types in `create_extension.py`**
   - Patch: `scripts/create_extension.py:20-35,59-157,168-220`.
   - Baseline: **Partial** — scaffolds the 4 declarative types and explicitly rejects deferred hook/mcp (`:19-45,70-169`); no plugin support.
   - Verdict: **want** scaffolding for the 4 existing types; **skip** runtime/bundle scaffolds.

7. **Type-aware discovery/catalog generation across all 7 type roots**
   - Patch: `scripts/marketplace.py:24-50,205-280,930-1009`; tests `:45-70,96-109`.
   - Baseline: **Partial** — already discovers/catalogs the 4 v1 roots and emits type from directory (`:30-39,205-218,969-977`); no consistency check between manifest `type` and directory, no entrypoint metadata in catalog.
   - Verdict: **want** the consistency/metadata improvements for 4 types; **skip** additional roots.

8. **Runtime-type inspection for hooks/MCP (reject undeclared commands/network/secrets, unsafe MCP URLs, never start servers)**
   - Patch: `scripts/marketplace.py` runtime-validation additions (13821-15042 range); tests `:125-196`.
   - Baseline: **No** — baseline fail-closed blocks runtime filenames (`hooks.json`, `mcp.json`, `.mcp.json`) outright (`scripts/marketplace.py:58-64`) and documents hooks/MCP as deferred (`spec/ASSET_SPEC.md:3-5`).
   - Verdict: **skip** — explicitly out of lean-v1 scope; keep current fail-closed/deferred behavior unchanged.

9. **Plugin bundle validation (`plugin.json`/`.claude-plugin/plugin.json`, nested skills/hooks/agents/MCP, Copilot-specific components)**
   - Patch: `docs/EXTENSION_TYPES.md:33-37`; `scripts/marketplace.py` plugin additions; tests `:198-225`.
   - Baseline: **No** — no plugin type/dir/schema/tests anywhere; `GLOSSARY.md:7-9` explicitly scopes supported kinds to skill/instructions/prompt/agent and advises avoiding "Plugin".
   - Verdict: **skip** — explicitly out of lean-v1 scope.

10. **Finder taxonomy extended to 7 types, auto-install still limited to skills**
    - Patch: `scripts/find_extension.py:37-55,177-188,252-316,666-728`; `docs/EXTENSION_TYPES.md:38-46`.
    - Baseline: **Partial** — recognizes 6 types but only auto-installs skills, publishes 4 declarative types (`:35-53,205-213,258-266`).
    - Verdict: **want** the 4-type search/catalog handling and skill-only install; **skip** runtime/plugin finder support.

11. **Add `docs/EXTENSION_TYPES.md` + generated `docs/types.html`**
    - Patch: `docs/EXTENSION_TYPES.md:1-46`; `docs/_pages/types.html:1-20`; built `docs/types.html:10594-12362`.
    - Baseline: **Partial** — 4 types documented across `spec/ASSET_SPEC.md:1-60`, `spec/SKILL_SPEC.md:1-8`, `GLOSSARY.md:7-28`; no dedicated `EXTENSION_TYPES.md`/`types.html` exists.
    - Verdict: **want** a concise 4-type guide; omit hook/MCP/plugin taxonomy or mark it explicitly future-scope.

12. **New consolidated `tests/test_extension_model.py` (discovery, validation, cataloging, type/dir matching, entrypoint traversal, duplicate IDs, runtime inspection, plugins)**
    - Patch: `tests/test_extension_model.py:1-436` (patch lines 16835-17276).
    - Baseline: **No** such file exists; current tests are `test_marketplace.py`, `test_companions.py`, `test_validate_skill.py`.
    - Verdict: **want** the v1-relevant subset (discovery/validation/cataloging/entrypoint-safety/duplicate-IDs for the 4 types); **skip** hook/MCP/plugin test cases.

---

## 3. Scan / policy

Patch files: `docs/COMMUNITY_INTAKE_POLICY.md` (2178-2299), `docs/REVIEW_GUIDE.md` (2570-2611, new), `scripts/scan_contributions.py` (15311-15461, new), `scripts/rescan_candidate.py` (15185-15310), `tests/fixtures/marketplace/adversarial-cases.json` (16152-16249), `.github/workflows/community-intake.yml` (189-386, full), `.github/workflows/federated-candidate.yml` (436-514, full), `config/marketplace.yaml` (2047-2115).

**This is the most consequential area** — the patch's core policy model is incompatible with the lean-v1 contribution model stated in the issue.

1. **Replace community auto-publication with mandatory owner/CODEOWNER review for every extension**
   - Patch: `docs/COMMUNITY_INTAKE_POLICY.md:1-27`; `docs/REVIEW_GUIDE.md:1-36`; `config/marketplace.yaml:2-31`.
   - Baseline: **No / contradictory** — baseline policy states community packages publish on automated checks alone and are never "Reviewed" (`docs/COMMUNITY_INTAKE_POLICY.md:1-8`); workflow explicitly supports `auto-publish` decisions (`.github/workflows/community-intake.yml:3-9,137-183`); `marketplace.py` classifies clean submissions as `intake_decision`-eligible (`:650-710`).
   - Verdict: **skip** — directly contradicts the stated lean-v1 model ("community extensions auto-publish after passing deterministic scans").

2. **Add a maintainer review guide + evidence checklist (`docs/REVIEW_GUIDE.md`)**
   - Patch: `docs/REVIEW_GUIDE.md:1-36`.
   - Baseline: **No** such file; baseline policy docs are automated-intake only (`docs/COMMUNITY_INTAKE_POLICY.md:1-102`).
   - Verdict: **maybe** — useful for the **specialty/team-reviewed** path only; most of its mandatory-owner-review framing is unneeded for auto-published community skills.

3. **Retire org-membership/account-age/velocity anti-abuse gates in favor of read-only evidence scanning**
   - Patch: `docs/COMMUNITY_INTAKE_POLICY.md:6-27,38-42`; `.github/workflows/community-intake.yml:1-68`; `config/marketplace.yaml:20-31`.
   - Baseline: **No / contradictory** — baseline makes org membership a hard eligibility gate and documents account-age/velocity controls (`docs/COMMUNITY_INTAKE_POLICY.md:3-12,46-83`); workflow calls membership API / resolves account age / open PRs (`:24-125`); config has `min-account-age-days`, `max-open-submissions-per-author`, risk ceiling (`config/marketplace.yaml:20-40`).
   - Verdict: **skip** — these anti-abuse gates are central to baseline's existing design and are not a substitute for deterministic scanning; removing them weakens rather than lean-ifies v1.

4. **New `scripts/scan_contributions.py`: trusted-base scanner for every changed package (incl. non-manifest edits/removals, symlinks, explicit full-SHA revisions)**
   - Patch: `scripts/scan_contributions.py:1-145` (patch 15311-15461).
   - Baseline: **No file** — equivalent logic lives in `scripts/marketplace.py` (regular-file/symlink/special-file checks `:282-327`, text scanning `:332-379`, package scan/digests `:650-710`); baseline workflow only scans changed community-manifest paths, not arbitrary file changes (`.github/workflows/community-intake.yml:137-151`).
   - Verdict: **want** — trusted-base policy, immutable-revision checks, and scanning non-manifest edits are all directly valuable for deterministic v1 intake. Restrict active directories to `skill/prompt/instructions/agent`; drop hooks/mcp/plugins.

5. **Preserve scanner findings + content digests as machine-readable contribution evidence**
   - Patch: `scripts/scan_contributions.py:65-145`.
   - Baseline: **Partial** — baseline already generates findings and package-tree/content digests (`scripts/marketplace.py:264-379,650-710`) and catalog records carry `content-digest`/policy data (`:950-1035`); no separate revision-bound evidence artifact exists.
   - Verdict: **want** — improves reproducibility/auditability without changing the auto-publish model.

6. **Stronger candidate-issue parsing/provenance in `rescan_candidate.py`**
   - Patch: `scripts/rescan_candidate.py:35-65,88-127,136-193` (64 KiB body limit, duplicate-heading rejection, active/skill-only approved sources, scanner-error handling, issue-body digest + marketplace revision + workflow-run identity, "submitter-claimed" provenance labeling).
   - Baseline: **Partial** — baseline parses exact headings, validates fields/digest JSON, invokes `_scan_source`, compares package-tree digest, reports findings (`scripts/rescan_candidate.py:34-140`), but lacks the size/duplicate-field defenses and explicit evidence identity.
   - Verdict: **want** — strong hardening for the federated/candidate path; provenance labeling is especially on point.

7. **Separate candidate scanning (read-only) from issue-comment write permissions**
   - Patch: `.github/workflows/federated-candidate.yml:1-65`.
   - Baseline: **Partial** — deny-all top-level permissions plus read contents + issue write all in one job (`:1-20`); scan and comment happen in the same job (`:21-50`).
   - Verdict: **want** — meaningful token-boundary improvement, low friction.

8. **Run contribution scanning from a trusted-policy checkout; drop privileged membership tokens**
   - Patch: `.github/workflows/community-intake.yml:1-68`.
   - Baseline: **Partial / materially weaker** — baseline has `contents: read` but also `pull-requests: write`, `ORG_READ_TOKEN || github.token`, membership API + GitHub search calls (`:24-125`), and invokes `marketplace.py intake` from the checked-out tree (`:137-183`).
   - Verdict: **want** the trusted-policy-checkout + least-privilege shape — **but preserve** baseline's existing membership/anti-abuse checks (see item 3) rather than deleting them.

9. **Upload immutable scan/rescan evidence as workflow artifacts (pinned action SHAs, bounded retention)**
   - Patch: `.github/workflows/community-intake.yml:56-68`; `.github/workflows/federated-candidate.yml:31-65`.
   - Baseline: **No** — baseline writes only a step summary/labels (`community-intake.yml:151-183`) and comments directly without evidence upload (`federated-candidate.yml:35-50`).
   - Verdict: **want** — useful auditability.

10. **Add `additional-review-risk-threshold` + package `withdrawals: []`**
    - Patch: `config/marketplace.yaml:13-31`; `docs/REVIEW_GUIDE.md:20-31`.
    - Baseline: **Partial** — risk/advisory computation and digest-pinned review records already exist (`scripts/marketplace.py:332-430,986-1000`; `config/marketplace.yaml:9-18`); no withdrawal key; config validation rejects unexpected keys (`scripts/marketplace.py:850-889`).
    - Verdict: **maybe** — risk escalation only matters if a workflow enforces it; withdrawals are operationally useful for incident response but are a catalog/release feature, not an intake-gate feature.

11. **Restrict candidate rescans to active, `skill`-advertising approved discovery sources**
    - Patch: `scripts/rescan_candidate.py:65-71`; `config/marketplace.yaml:22-31`.
    - Baseline: **Partial** — approved sources with status/types already exist and are schema-validated (`config/marketplace.yaml:41-63`; `scripts/marketplace.py:770-830`), but `rescan_candidate.py` currently accepts every configured catalog regardless of status/type (`:56-63`).
    - Verdict: **want** — fits v1's active-skill-only federated-candidate path.

12. **Deepen the adversarial "excessive resource depth" fixture (nested path → 5 directories)**
    - Patch: `tests/fixtures/marketplace/adversarial-cases.json:3-81` (patch 16152-16249).
    - Baseline: **Partial** — same fixture family exists (secrets, hidden unicode, blocked types, archives, unsupported files, exec bits, scripts, network, env vars); baseline's current nested-resource case is shallower (`references/nested/payload.md`).
    - Verdict: **want** — deterministic path-depth coverage is useful if the scanner enforces a depth limit; most other diffs are JSON formatting only.

13. **General framing drift toward hooks/MCP/plugins as scannable types**
    - Patch: `scripts/scan_contributions.py:16-24`; `.github/workflows/community-intake.yml:9-16`; `docs/REVIEW_GUIDE.md:20-25`.
    - Baseline: baseline recognizes deferred `hook`/`mcp` types in code comments but keeps them deferred (`scripts/marketplace.py:900-906`) and its active/community path detection is limited to `skills/prompts/instructions/agents` (`.github/workflows/community-intake.yml:46-55`).
    - Verdict: **skip** broadening — stay within the 4-type v1 scope.

---

## 4. Catalog UI

Patch files: `catalog/catalog.json` (1412-2046), `docs/_generated/catalog-cards.html` (2612-2670), `docs/_pages/catalog.html` (2748-3245), `docs/assets/catalog-core.js` (4380-4479, new), `docs/assets/catalog.js` (4480-4734), `docs/assets/catalog.json` (4735-5369), `docs/assets/search-index.json` (5370-5378), `docs/assets/search.js` (5379-5598), `docs/build-pages.js` (5599-5687), `docs/catalog.html` (5688-6469), `docs/generate-search-index.js` (7354-7426), `tests/test_catalog_ui.js` (16250-16387, new).

Baseline already has a substantial static-site/catalog pipeline — this is enhancement of existing tooling, not new concept.

1. **Catalog record enrichment (`compatibility`, `entrypoint`, `installation`, `usage`, policy-version bump)**
   - Patch: `catalog/catalog.json:1412-2046`.
   - Baseline: **Partial** — baseline catalog already has type/digests/compatibility/review-evidence/policy results (`catalog/catalog.json:75-131,154-230,1045-1049`), but not `installation`/`entrypoint`/`usage` consistently.
   - Verdict: **want, narrow** — keep deterministic metadata/evidence fields; defer broad installer metadata and anything for out-of-scope types.

2. **Generated static catalog cards with searchable data attributes (type, specialty, review status, lifecycle, risk, declared access)**
   - Patch: `docs/_generated/catalog-cards.html:2612-2670`.
   - Baseline: **Yes/partial** — same generated-card projection and row structure already exist (`docs/_generated/catalog-cards.html:1-21,24-45,~190`); patch mainly changes vocabulary/metadata.
   - Verdict: **want** — static, no-JS cards are the simplest useful catalog surface; limit displayed types to the 4 v1 types.

3. **Faceted, browsable catalog page (search, facets, detail panel, access indicators, noscript fallback, a11y)**
   - Patch: `docs/_pages/catalog.html:2748-3245`; built `docs/catalog.html:5688-6469`.
   - Baseline: **Yes, substantially** — source page already has the rail, search, facets, result list, detail panel, reset, generated-card placeholder, noscript fallback (`docs/_pages/catalog.html:1-57`); built page already has extensive styling/UI (`docs/catalog.html:365-441`+).
   - Verdict: **want, simplified** — keep search + type/status/access filters + evidence details; defer richer vocabulary/install UX until more than 4 types exist.

4. **New dependency-free `catalog-core.js` (HTML escaping, HTTPS/immutable-source URL validation, token/facet matching, review-staleness handling, fail-closed installer-command generation)**
   - Patch: `docs/assets/catalog-core.js:4380-4479`.
   - Baseline: **No** — `docs/assets/` has `catalog.json`, `search-index.json`, `search.js`, but no shared `catalog-core.js`; equivalent logic is embedded directly in `docs/catalog.html`.
   - Verdict: **want** — small, high-value hardening for immutable-source links and fail-closed install; implement for skill installation only initially.

5. **Client-side filtering/detail logic extracted to `catalog.js` (URL-state sync, pinned install commands)**
   - Patch: `docs/assets/catalog.js:4480-4734`.
   - Baseline: **Partial** — filtering/facets/detail rendering already implemented inline in `docs/_pages/catalog.html:75-180` / built `docs/catalog.html`; no standalone `catalog.js` exists.
   - Verdict: **maybe** — keep existing inline/static behavior for v1; only extract if it reduces duplication or is needed for installer safety/URL-state.

6. **Catalog JSON / search-index browser projections**
   - Patch: `docs/assets/catalog.json:4735-5369`; `docs/assets/search-index.json:5370-5378`.
   - Baseline: **Yes** — both already exist with release metadata (`docs/assets/catalog.json:1045-1049`) consumed by `docs/assets/search.js:1-15,89-130`.
   - Verdict: **want** — keep static machine-readable artifacts; don't add projections for unsupported types.

7. **Search-index generation hardening (`<main>`-only scoping, exclude scripts/styles/comments/nav/footer, no ID collisions, importable `processPage`)**
   - Patch: `docs/generate-search-index.js:7354-7426`.
   - Baseline: **Partial** — `stripHtml`/`processPage`/heading extraction/generated output already exist (`docs/generate-search-index.js:34,89-158,208`), but without `<main>` scoping, executable-content exclusion, or an exported `processPage`.
   - Verdict: **want** — low-cost correctness/security hardening.

8. **Deterministic build/release-state pipeline (release-date or `SOURCE_DATE_EPOCH`, `aria-current`, companion-install authorization, suppressed install commands in dev releases)**
   - Patch: `docs/build-pages.js:5599-5687`.
   - Baseline: **Partial** — build pipeline + release-config parsing + card substitution already exist (`docs/build-pages.js:1-52,53-94`), but uses wall-clock `new Date()` (`:10-13`) and emits preview install language even in dev (`:39-52`), with no `COMPANION_INSTALL` handling.
   - Verdict: **want** — deterministic builds and no install-in-dev are important; scope companion authorization to the two existing companion skills.

9. **Client-side documentation search refinements**
   - Patch: `docs/assets/search.js:5379-5598`.
   - Baseline: **Yes, substantially** — baseline already implements full client-side search (`docs/assets/search.js:1-15,89-130,134-220+`).
   - Verdict: **maybe** — retain existing search; prioritize catalog search/facets over further search-engine sophistication.

10. **New JS test harness `tests/test_catalog_ui.js` (token/facet search, HTML/link escaping, immutable source URLs, pinned installer commands, type vocabulary, search-index boundaries, preview-page behavior)**
    - Patch: `tests/test_catalog_ui.js:16250-16387`.
    - Baseline: **No** — `tests/` only has `test_companions.py`, `test_marketplace.py`, `test_validate_skill.py`.
    - Verdict: **want, targeted** — cover fail-closed installer generation, safe source URLs, deterministic indexing, dev-release behavior; defer exhaustive browser/UI testing. (Patch wires it into Makefile and PR CI — see §1 item 21 / §8 item 9.)

11. **`_pages`/`_generated`/static-build concept itself**
    - Baseline: **Yes** — this entire generation model (source pages → generated cards/pages) already exists in baseline; the patch is an enhancement, not a new architecture.

---

## 5. Companion skills

Patch files: `skills/community/bcgov-create-extension/{SKILL.md (15462-15557), bcgov-extension.yaml (15558-15612), references/SUBMISSION.md (15613-15708), references/writing-agents.md (15709-15731), references/writing-instructions.md (15732-15754), references/writing-prompts.md (15755-15776), references/writing-runtime.md (15777-15814, new)}`, `skills/community/bcgov-find-extension/{SKILL.md (15815-15910), bcgov-extension.yaml (15911-15977), references/INSTALLATION.md (15978-16106), references/THIRD_PARTY.md (16107-16151)}`, `tests/test_companions.py` (16388-16834).

Baseline `skills/community/` already contains **8** skills including both `bcgov-create-extension` and `bcgov-find-extension` — the patch is an **enhancement of existing companions**, not a new introduction. Baseline `tests/test_companions.py` already exercises most of the same contract (`tests/test_companions.py:40-710`, verified directly).

1. **Guided "create extension" companion — explicit untrusted-input handling, capability disclosure, removal instructions, handoff-vs-submission boundaries**
   - Patch: `bcgov-create-extension/SKILL.md:15462-15557`.
   - Baseline: **Yes, partial** — companion and authoring flow already exist (`skills/community/bcgov-create-extension/SKILL.md:1-59`; tested at `tests/test_companions.py:40-95`).
   - Verdict: **want** — directly supports the skill/PR/GitHub-UI contribution model; omit deferred runtime types.

2. **Guided "find extension" companion — update/remove actions, client compatibility, project-scoped install previews**
   - Patch: `bcgov-find-extension/SKILL.md:15815-15910`.
   - Baseline: **Yes, partial** — workflow already implemented (`skills/community/bcgov-find-extension/SKILL.md:1-59`; tested `tests/test_companions.py:101-226`).
   - Verdict: **want** — discovery/safe install is central to v1 consumption; keep active skill discovery/install, defer update/remove until the install contract supports it.

3. **Per-type writing guides (`writing-agents.md`, `writing-instructions.md`, `writing-prompts.md`) + new `writing-runtime.md`**
   - Patch: 15709-15814.
   - Baseline: **Yes for the first three; no for runtime** — baseline already has `writing-agents.md`/`writing-instructions.md`/`writing-prompts.md`/`writing-skills.md` (tested `tests/test_companions.py:55-82`); shared structure enforced via `spec/SKILL_SPEC.md:18-61`; `writing-runtime.md` doesn't exist and baseline tests expect exactly 4 declarative guides.
   - Verdict: **want** for skill/instructions/prompt/agent guides; **skip** `writing-runtime.md` (hooks/MCP/plugins out of scope — patch itself frames it as deferred).

4. **Portable submission workflow (stage public files only, inspect capabilities/provenance, schema-validate, full diff, explicit confirmation, draft PR / recovery path)**
   - Patch: `references/SUBMISSION.md:15613-15708`.
   - Baseline: **Yes, partial** — already exists (`skills/community/bcgov-create-extension/references/SUBMISSION.md:1-49`); tested at `tests/test_companions.py:352-421,597-613`.
   - Verdict: **want** — maps directly to the skill/PR/GitHub-UI contribution path; patch mainly strengthens authorization-boundary language.

5. **Installation instructions (exact-revision install, APM-preferred/`npx skills@…` fallback, byte/receipt verification, uninstall/rollback)**
   - Patch: `references/INSTALLATION.md:15978-16106`.
   - Baseline: **Yes, substantial** — already states install is active only for Agent Skills (`skills/community/bcgov-find-extension/references/INSTALLATION.md:1-58`); tested at `tests/test_companions.py:101-110,449-477,642-658`.
   - Verdict: **want** — core v1 consumer path; keep exact-revision/confirm/verify/uninstall guidance, avoid promising update/remove not yet implemented.

6. **Third-party/federated discovery + registration (approved sources only, inspect immutable bytes/ownership/license/capabilities, register for review rather than direct install)**
   - Patch: `references/THIRD_PARTY.md:16107-16151`.
   - Baseline: **Yes, substantial** — already implemented (`skills/community/bcgov-find-extension/references/THIRD_PARTY.md:1-86`; tested `tests/test_companions.py:198-226,479-596`).
   - Verdict: **maybe/want** — useful for marketplace growth, but keep bounded to the currently-supported skill type and existing approved-source workflow.

7. **Companion `bcgov-extension.yaml` manifests expanded to 7 types**
   - Patch: 15558-15612, 15911-15977.
   - Baseline: **Yes, partial** — both manifests exist (`.../bcgov-create-extension/bcgov-extension.yaml:1-25`, `.../bcgov-find-extension/bcgov-extension.yaml:1-23`); tested `tests/test_companions.py:352-421,660-670`.
   - Verdict: **maybe** — keep metadata aligned to actual v1 support; don't advertise hook/mcp/plugin or unsupported install actions.

8. **`tests/test_companions.py` patch delta vs. baseline** — baseline already covers companion presence/self-containment (`:40-95`), catalog search/fallback (`:101-294`), scaffolding + deferred executable integrations (`:297-350`), secret/capability scanning (`:352-421`), install/receipt verification (`:422-477`), third-party/federated behavior (`:479-596`), public-diff/scaffolding (`:597-629`), docs (`:630-659`), catalog consistency (`:660-710`). The patch version **changes** rather than adds: requires `writing-runtime.md`, adjusts fallback metadata wording, replaces "reserved prompt types must fail" with "all extension types scaffold," switches candidate registration to `--body-file`, and shifts getting-started expectations to release/catalog/consume-page text.
   - Verdict: **mostly skip the policy change** (all-type scaffolding conflicts with v1's 4-type scope — baseline's "deferred executable integrations blocked" behavior should stay); **want** the install/receipt/digest hardening additions layered after that point.

---

## 6. Docs / governance

Patch files: `AGENTS.md` (1049-1068), `CONTRIBUTING.md` (1069-1153), `README.md` (1174-1320), `SECURITY.md` (1321-1411), `docs/ADMIN_SETUP.md` (2132-2177, new), `docs/GOVERNANCE.md` (2352-2404, new), `docs/MARKETPLACE_DECISIONS.md` (2405-2441), `docs/MARKETPLACE_RUNBOOK.md` (2442-2524), `docs/README.md` (2525-2569), `docs/how-to-use-the-marketplace.md` (9654-9771), `docs/what-is-the-agent-marketplace.md` (12363-12436), `docs/marketplace-reference.md` (10060-10190), `docs/getting-started.md` (7755-7874) plus generated/source HTML duplicates (`docs/_pages/*`, `docs/_partials/*`, `docs/_generated/*`, `docs/assets/*`, `docs/{index,getting-started,consume,contribute,faq,architecture,spec,governance,types}.html`), `tests/test_governance.py` (17277-17502, new), and `.mcp.json` (1031-1048, out of scope).

1. **Repository contribution guardrails (`AGENTS.md`)** — untrusted-content handling, no-execution-during-validation, centrally-controlled review fields, digest invalidation, privileged-workflow boundaries, native-format boundaries, static-site regen requirement.
   - Baseline: **Partial** — baseline `AGENTS.md:1-13` covers issue tracking/labels/glossary/ADR references only, lacks these governance rules.
   - Verdict: **want** — trim references to unsupported hooks/MCP/plugins and to absent docs (`EXTENSION_TYPES.md` etc.) before adopting.

2. **Contributor workflow / package governance (`CONTRIBUTING.md`)** — broadens to 7 types, adds public-output authorization, compatibility/removal guidance, behavior examples, account handoff.
   - Baseline: **Partial** — already has signed commits, companion-based authoring, 4 supported types, manifests, capability declarations, upstream-search evidence, generated-catalog changes, federated candidates (`CONTRIBUTING.md:1-69`).
   - Verdict: **want, narrowed** — keep clearer contribution/evidence rules for the 4 v1 types; skip 7-type/runtime requirements.

3. **Expanded security policy (`SECURITY.md`)** — no-SLA wording, broader type scope, scan/review/runtime-approval distinctions, admin-only GitHub controls, tag/environment protection, Actions restrictions, containment/recovery.
   - Baseline: **Partial** — already covers private reporting, immutable revision/digest evidence, quarantine, scope, public follow-up (`SECURITY.md:1-17`).
   - Verdict: **want, narrowed** — adopt trust-boundary/recovery language; skip unsupported-type scope and detailed admin checklists.

4. **New `docs/ADMIN_SETUP.md`** — verification/bootstrap document for protected branches, CODEOWNERS, Pages, release tags, scanner bootstrap.
   - Baseline: **No** such file; partial overlap in `docs/MARKETPLACE_RUNBOOK.md:1-56`.
   - Verdict: **maybe** — useful for real publication rollout; defer scanner-bootstrap/unsupported-type controls until v1 workflow exists.

5. **New `docs/GOVERNANCE.md`** — separates scan results / publication approval / domain review / consuming-team authorization.
   - Baseline: **No** dedicated doc; material is scattered across `docs/MARKETPLACE_DECISIONS.md:1-16`, `docs/MARKETPLACE_RUNBOOK.md:1-56`, `SECURITY.md:1-17`, `docs/what-is-the-agent-marketplace.md:1-66`.
   - Verdict: **want** — a short governance doc separating these concerns is valuable for v1; strip MCP/plugin-specific language.

6. **Decision-log modernization (`docs/MARKETPLACE_DECISIONS.md`)** — reframes as a 7-type contract, adds lifecycle withdrawal, runtime boundaries, immutable-release decisions.
   - Baseline: **Yes, partial** — already records companion naming, discovery sources, blocking policy, ownership/license, SHA/digest model, supported hosts (`:1-16`).
   - Verdict: **want, narrowed** — update for the 4-type model and publication/review semantics; reject 7-type scope.

7. **Operations runbook expansion (`docs/MARKETPLACE_RUNBOOK.md`)** — rigorous immutable-release procedure, separate source/catalog commits, protected release tags/environments, partial-release handling.
   - Baseline: **Yes, substantial** — already covers ownership, access, intake checks, publication, federated candidates, quarantine, removal, rollback, recovery (`:1-56`).
   - Verdict: **want** — the immutable-release/recovery clarifications are directly useful; omit unsupported native-integration procedures.

8. **Documentation index refresh (`docs/README.md`)** — audience table, governance/admin/review links, generated-file/build caveats.
   - Baseline: **Partial/mostly yes** — already documents static site, Diátaxis guides, `make generate`/`make docs`, source-vs-generated split, search indexing, Pages (`:1-23`).
   - Verdict: **want, narrowed** — retain concise build guidance; avoid linking to absent `EXTENSION_TYPES.md`/`REVIEW_GUIDE.md` until they exist.

9. **User how-to workflow (`docs/how-to-use-the-marketplace.md`)** — comparison criteria, lifecycle/review-freshness checks, project-local receipts, update/removal safeguards.
   - Baseline: **Yes, partial** — already covers discovery, pinned install, creation, PR evidence, candidates, quarantine/removal/rollback, type scope (`:1-96`).
   - Verdict: **want, narrowed** — improve discovery/evidence/install/update/removal guidance for the 4 v1 types; skip hooks/MCP/plugins.

10. **Marketplace overview (`docs/what-is-the-agent-marketplace.md`)** and **technical reference (`docs/marketplace-reference.md`)** — both already substantially present in baseline with the 4-type model (`:1-66`, `:1-94`); patch adds central review/withdrawal semantics and references to not-yet-existing scripts (`scan_contributions.py`, `prepare_release.py`).
    - Verdict: **want, narrowed** — strengthen digest/review/lifecycle semantics; drop references to absent scripts/unsupported types.

11. **Getting-started tutorial (`docs/getting-started.md`)**
    - Baseline: **Yes, substantial** — already covers companion install, discovery, evidence inspection, install, creation, scope (`:1-106`).
    - Verdict: **want, narrowed** — retain "development release blocks installs" + exact SHA/digest inspection + local receipt guidance; keep the 4-type scope.

12. **Static documentation-site subsystem (`_pages`/`_partials`/`_generated`/`assets`, `build-pages.js`, `generate-search-index.js`, generated HTML for index/getting-started/consume/contribute/faq/spec/catalog)** — treated as ONE finding.
    - Baseline: **Yes** — the entire generation model already exists (`docs/_pages/`, `docs/_generated/`, `docs/_partials/`, `docs/assets/`, `docs/build-pages.js`, `docs/generate-search-index.js`, and generated `catalog.html`/`consume.html`/`contribute.html`/`faq.html`/`getting-started.html`/`index.html`/`spec.html` all already present). Only `docs/architecture.html`, `docs/governance.html`, `docs/types.html`, and `docs/_pages/governance.html` are genuinely new/absent.
    - Patch's substantive content here: a new governance page, and copy/navigation changes toward a 7-type narrative.
    - Verdict: **maybe** — keep the existing site; add a governance page only if `docs/GOVERNANCE.md` (item 5) is adopted; a 7-type-wide copy refresh is not needed — refresh copy only to the extent it stays accurate to the 4-type lean v1.

13. **Governance website page (`docs/_pages/governance.html` + built `docs/governance.html`)**
    - Baseline: **No** — doesn't exist; governance info is scattered across markdown docs.
    - Verdict: **maybe** — small rendered summary if `docs/GOVERNANCE.md` is adopted, otherwise markdown suffices.

14. **Homepage/generated-page copy refresh toward 7-type narrative**
    - Baseline: site exists but describes the 4-type/skill-first MVP, not 7 types.
    - Verdict: **maybe** — refresh only copy accurate to 4 types; skip the 7-type framing.

15. **New `tests/test_governance.py`**
    - Baseline: **No** such file; depends on absent `scan_contributions.py`/`prepare_release.py`.
    - Verdict: **maybe** — add focused tests only alongside the actual governance/release tooling that's adopted, not wholesale.

16. **`.mcp.json` (out of scope)** — MCP dev-authoring config; baseline doesn't have this exact file but `docs/CLEANUP_CHANGELOG.md:19-23` explains an equivalent is retained only for local codegraph authoring, unrelated to marketplace publication. Not analyzed further — hooks/MCP/plugins out of scope for v1.

---

## 7. Release

Patch files: `.github/workflows/release.yml` (814-1030), `.github/workflows/pages.yml` (515-602), `scripts/prepare_release.py` (15043-15184, new), `digests.txt` (2116-2131, deleted from repo root in patch).

1. **`scripts/prepare_release.py`: immutable snapshot validation + asset generation (validates full source commit/ancestry/clean checkout/published catalog/version/pinned packages/digests/catalog projections; emits `catalog.json`, `digests.txt`, `release-evidence.json` without mutating the repo)**
   - Patch: `scripts/prepare_release.py:1-136`.
   - Baseline: **Partial** — validation/generation already exists via `scripts/marketplace.py` (invoked from `Makefile:20-24`); release prep is currently a **manual** documented procedure (update immutable revision, set `release-state: published`, regenerate, `make verify`, record digests) in `docs/MARKETPLACE_RUNBOOK.md:17-19`; no `scripts/prepare_release.py` exists (baseline `scripts/` = create_extension/demo/find_extension/marketplace/rescan_candidate/validate_skill); baseline's identity model already requires full Git SHA + package-tree SHA-256 (`docs/MARKETPLACE_DECISIONS.md:14`).
   - Verdict: **maybe** — digest/source verification is valuable, but a dedicated release-prep script is more formal tooling than a lean v1's initial auto-publish/team-review flow needs; defer unless releases become frequent or security-sensitive.

2. **Release workflow: manual, protected publication (workflow_dispatch + exact reviewed commit + CalVer tag; read-only `prepare` job; protected `marketplace-release` environment; minimally-scoped `publish` job creating an immutable tag + GitHub Release) replacing automatic release-on-push**
   - Patch: `.github/workflows/release.yml:1-108`.
   - Baseline: **Partial** — baseline already has an **automatic** CalVer release on `main` pushes (tag calc, version/revision stamping, regen, digest creation, commit/tag push, GitHub Release) (`.github/workflows/release.yml:1-136`), i.e. it currently mutates protected `main` from Actions and auto-creates releases; docs already describe a manual release PR and say not to move release tags (`docs/MARKETPLACE_RUNBOOK.md:17-19,42-43`); config already carries CalVer version/revision (`config/marketplace.yaml:2-9`).
   - Verdict: **want** — the safety boundary (reviewed merged commit, no automatic main writes, protected publication, immutable tag) fits the lean contribution model and avoids release automation silently becoming an approval mechanism.

3. **GitHub Pages workflow hardening + trigger expansion to all supported extension/content dirs and scripts, action-SHA pinning, disabled persisted-credentials/caches, frozen deps, job timeouts**
   - Patch: `.github/workflows/pages.yml:1-99`.
   - Baseline: **Partial** — already has push/manual/weekly triggers, marketplace validation, `docs/build.sh`, artifact upload, Pages deploy (`:1-87`); trigger coverage is narrower (`skills/**` only, not prompts/instructions/agents or scripts) (`:8-22`); actions are version-tagged not SHA-pinned, caches enabled, no timeouts/`persist-credentials:false` (`:40-70,76-87`).
   - Verdict: **want** — publishing the catalog/docs is useful now, and trigger coverage must follow the 4 supported types; hardening is low-cost supply-chain hygiene. Weekly rebuild is optional.

4. **Digest manifest/provenance asset moved from checked-in `digests.txt` to release-attached generation**
   - Patch: `digests.txt` deletion; generation moves into `prepare_release.py:104-112` and `.github/workflows/release.yml:88-108`.
   - Baseline: **Partial** — already has a checked-in digest manifest with catalog revision + package SHA-256 (`digests.txt:1-10`); catalog already records package content digests directly (`catalog/catalog.json:78-1049`); baseline's automatic release workflow also generates a digest manifest (`.github/workflows/release.yml:108-115`); runbook requires recording catalog/package digests + source commit in the release PR (`docs/MARKETPLACE_RUNBOOK.md:17-19`).
   - Verdict: **maybe** — package digests + full source SHAs are already part of the MVP integrity model; a separate release-attached manifest/evidence file can be deferred if the catalog + install lockfile already provide sufficient verification; retain only if/when immutable public releases are enabled.

---

## 8. Tests

Note: per-file content of `test_catalog_ui.js`, `test_extension_model.py`, and the `adversarial-cases.json` fixture is covered in depth in §3/§4/§2; this section covers overall test-suite inventory, meta-level gaps, and whether the baseline suite currently passes.

1. **New `tests/test_catalog_ui.js` — Node `node:test` harness** (token/facet search, HTML/link escaping, immutable GitHub source URLs, pinned installer commands, publish/install eligibility, supported-type vocabulary, search-index boundaries, preview-page behavior).
   - Patch: 16250-16387 (tests begin ~16271 onward).
   - Baseline: **No** — `tests/` has only `test_companions.py`, `test_marketplace.py`, `test_validate_skill.py`; no JS tests/Node target; `Makefile:29-31` runs `uv run pytest -q` only.
   - Verdict: **want with the patch's verification wiring** (see item 9) — directly supports deterministic-scan/auto-publish safety for v1 skills; avoid expanding assertions to out-of-scope types.

2. **`test_companions.py` broadened from "deferred types must fail" to "all types scaffold"**
   - Patch: 16426-16494, 16555-16823.
   - Baseline: **Partial** — baseline already tests type scaffolding (`tests/test_companions.py:297-334`) but separately keeps executable integrations deferred and blocks reserved-type installation (`:324-350`); patch changes that policy and adds substantial install/receipt/supply-chain coverage.
   - Verdict: **mostly skip the policy change** — keep inert scaffolding + unknown-type rejection; skip broad runtime-type activation tests since v1 types are skill/instructions/prompt/agent and auto-publish shouldn't imply runtime integration support.

3. **New companion installation-integrity/side-effect tests** (digest ordering, exact-byte install, catalog hold-before-download, non-skill inspection without config, unreviewed-candidate side-effect freedom, safe uninstall, symlink-escape prevention, receipt validation/tampering, duplicate registration, immutable source/release coordinates, submission-tooling integrity).
   - Patch: 16555-16823.
   - Baseline: **Partial** — related tests exist at `:422-479` (immutable source validation, copy verification, receipt tampering) and `:512-548` (rescan/digest), but not the broader hold-before-download/containment/uninstall-preservation/submission-tooling tests.
   - Verdict: **want** — directly relevant to safe pinned install and deterministic scan/review evidence even for the narrower v1 type set.

4. **Companion fallback/documentation assertions shift to release/preview semantics** (`local-fallback`/`local-snapshot`, release-banner/catalog/consume-page assertions replacing "portable workflow" assertions).
   - Patch: 16388-16425, 16504-16515.
   - Baseline: **Partial** — baseline tests fallback at `:228-247` (expects catalog unchanged) and docs assertions at `:630-640` (still requires direct `apm install`/`npx skills@` guidance).
   - Verdict: **want** — release-state/development-preview boundaries are central to "auto-publish after deterministic scan"; keep tests preventing preview/held content from exposing install paths.

5. **New `tests/test_extension_model.py`** (discovery/validation/cataloging across 7 types, canonical dir/type matching, safe entrypoint paths, duplicate IDs, MCP/runtime enforcement, plugin inspection, native-markdown runtime handling, lifecycle/withdrawal/review-expiry, wildcard risk, intake decisions, scanner failures, immutable Git inventory, release tags, workflow permissions).
   - Baseline: **Partial** — `tests/test_marketplace.py:212-236` covers the 4 v1 types; `:306-559` covers scanner/digest/review/intake behavior; no consolidated extension-model test file exists.
   - Verdict: **want the v1 subset** (canonical type discovery, entrypoint safety, IDs, deterministic scanning, review-expiry/content-digest invalidation, withdrawal, immutable inventory); **skip/defer** MCP/plugin/hook runtime-policy cases.

6. **Adversarial fixture strengthened** (see §3 item 12) — **want**.

7. **`test_marketplace.py` tiny diff (17503-17524): review status changes from `unreviewed` to `review-stale`; intake decision changes from auto-publishable to `hold-for-review` for a specific scenario**
   - Baseline: **Partial** — baseline has both tests (`:460-468`, `:505-514`) with the older (looser) expectations; baseline's 146 tests currently pass.
   - Verdict: **want** — content-digest invalidation and fail-closed review holds are essential safeguards around deterministic scanning and auto-publish; the test should explicitly preserve auto-publish only for genuinely clean, newly-scanned v1 submissions.

8. **Baseline-only `tests/test_validate_skill.py` has no patch equivalent** (60 test functions: frontmatter parsing `:86-115`, body validation `:253-305`, discovery/CLI `:326-448`, duplicate detection `:492-634`; `Makefile:9-13,47-55` still invokes the validator).
   - Verdict: **want/retain** — skills are a v1 extension type; this suite protects the existing skill contract and must not be silently dropped if the patch's test inventory is cherry-picked.

9. **Makefile/CI integration for the new JS suite** — the patch **does** add `node --test tests/test_catalog_ui.js` to `make test` and `make verify` (`Makefile`, patch lines 1154-1173) and to `.github/workflows/pr.yml` (patch lines 760-780); baseline runs pytest only (`Makefile:25-27,58-72`) with no JS test job.
   - Verdict: **want if the JS tests are retained, otherwise skip the harness** — adopt the patch's Node wiring with any selected JS tests so CI actually enforces them.

10. **Baseline suite status** — `uv run pytest tests/ -q` → **146 passed in 0.82s** (ran directly against baseline, read-only, no modifications). Baseline test coverage is healthy but currently Python-only.

---

## Top ideas worth mining for a lean v1

Ranked by how directly they advance "community auto-publish after deterministic scans / specialty team-review / contribution via skill-PR-GitHub-UI" without pulling in hook/MCP/plugin scope:

1. **Trusted-base contribution scanner (`scripts/scan_contributions.py` shape)** — scan every changed package (not just manifests) against a trusted-base policy checkout, with explicit full-SHA revisions and machine-readable evidence (§3.4-3.5). This is the single highest-value idea: it generalizes and hardens baseline's existing scanning without touching the auto-publish policy itself.
2. **Token-boundary separation in `community-intake.yml`/`federated-candidate.yml`** — read-only scan job → upload evidence artifact → separate write-permission job for comments/labels; deny-all + per-job grants; pinned actions/frozen deps/timeouts (§1.9-1.11, §3.7-3.9). Pure security hardening, zero policy conflict, cheap to adopt.
3. **Fork-PR checks instead of a hard fork-gate failure in `pr.yml`** (§1.16) — needed for the stated "contribution via PR/GitHub web UI" model to actually work for external community contributors.
4. **Explicit manifest `type` + `entrypoint` + `compatibility`/`usage` for the 4 v1 types, with untyped-skill backward compatibility** (§2.2-2.4) — the cleanest, lowest-risk slice of the 7-type taxonomy expansion; formalizes exactly what lean v1 needs and nothing more.
5. **Generalized PR template + extension-request/problem issue templates, scoped to the 4 types** (§1.3-1.7) — directly implements the "contribution via PR or GitHub web UI" channel; capability/access declarations make scans and specialty review easier to automate.
6. **Companion skill hardening (install byte/receipt verification, symlink-escape prevention, hold-before-download, immutable-source validation)** (§5.4-5.5, §8.3) — strengthens the skill/PR contribution and consumption paths baseline already has, with no scope creep.
7. **Deterministic/no-mutation release workflow (`workflow_dispatch` + reviewed commit + protected environment + immutable tag)** (§7.2) — fixes a real baseline gap (auto-release-on-push mutating `main`) in a way that fits "no silent approval via automation."
8. **Adversarial-fixture depth hardening + fail-closed review-status tests** (§3.12, §8.6-8.7) — small, concrete, deterministic-scan-relevant test improvements that reinforce rather than relax the auto-publish gate.
9. **`docs/GOVERNANCE.md` (short, scoped) separating scan-pass / specialty-review / consuming-team-authorization** (§6.5) — the one genuinely missing doc that would make the lean v1 model legible, provided it's trimmed to 4 types and doesn't promise mandatory human review for community content.
10. **`catalog-core.js` shared safe-rendering/fail-closed-install module** (§4.4) — small, isolated, high-leverage security hardening for the catalog UI baseline already mostly has.

**Explicitly reject from the patch:** mandatory CODEOWNER/owner review for community extensions, removal of org-membership/account-age/velocity anti-abuse gates, and any 7-type (hook/mcp/plugin) taxonomy, scaffolding, runtime inspection, or test coverage — all of these directly conflict with the stated lean-v1 scope and contribution model, even though they are a large fraction of the patch's line count (§2.1, §2.8-2.9, §3.1, §3.3, §5.8, §8.2).
