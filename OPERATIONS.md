# Marketplace operations

Repository administrators execute this runbook after dormant implementation reaches main. [#43](https://github.com/bcgov/agent-marketplace/issues/43) is the authoritative activation and before/after evidence record. It remains open until live controls, both promised automatic routes, publication and real credential retirement pass. Code tests and API schema validity are not actor-feasibility or live acceptance proof. [#48](https://github.com/bcgov/agent-marketplace/issues/48) separately requires genuine non-writer browser/fork journeys for all four types and Specialty reviewer delivery for both files.

## Current and intended state

Read-only inventory dated **2026-11-03**; refresh before changing settings. This table reports observed controls, not an applied migration. Record new API outputs and outcomes in #43 without secret values.

| Surface | Observed before activation | Intended after proved transition |
| --- | --- | --- |
| Main ruleset 24379494 | Deletion/non-fast-forward blocked; strict Actions `results`; one approval, CODEOWNERS, stale dismissal, resolved threads; signatures; CodeQL high-or-higher/errors; DeployKey and Admin **always** bypass | Layered A/B below, no A bypass, B PR-only bypass |
| `catalog-*` ruleset 24379547 | No-bypass update/deletion/non-fast-forward restrictions | Retain unchanged; separate creation-only rule |
| Actions | Default write; PR creation/approval allowed | Default read-only; PR creation/approval disabled |
| Fork approval | `first_time_contributors_new_to_github` | Retain if effective org policy allows; otherwise record org policy and manual approval path |
| Security | Secret scanning, push protection, non-provider patterns, validity and AI detection enabled; CodeQL rule present; Dependabot security updates disabled | Preserve GHAS/push protection/CodeQL; prove selected required controls and dependency route |
| Pages | `github-pages` custom branch policy permits only `main` | Preserve main-only deployment; prove OIDC/Pages flow |
| Release | `catalog-2026.10.01` exists, `immutable: false` | Enable immutable releases prospectively; old releases remain historical |
| Private reports | Enabled | Retain private reporting and test entry point |
| Credentials | `RELEASE_DEPLOY_KEY`, writable `DEPLOY_KEY` id **165187949**, `ORG_READ_TOKEN` | Retire actual unused credentials after proofs; stale `REPOSITORY_DEPLOY_KEY` references are not evidence of another working secret |
| V1 flags in `config/marketplace.yaml` | `publication.enabled: false`, `community-intake.auto-publish: false`, `dependency-intake.auto-merge: false` | Independently enable only after shared and own proofs |

Before-state metadata includes repository/rulesets, effective Actions/fork permissions, environment branch policies, release immutability, GHAS, secret names/key IDs and consumer inventory. Never retrieve or print secret/key values. Re-list workflow consumers at the exact merged main revision: old release/Pages and Community/dependency automerge workflows are removed; no operational deploy-key or ORG_READ_TOKEN consumer remains in v1. New workflows use the built-in short-lived token; Pages additionally needs its scoped Pages/OIDC permissions. Check organization/environment/external consumers before deleting a credential.

## Stage 1: feasibility with flags off

- [ ] Confirm the merged revision, all three false flags, successful `make verify`, PR checks and absence of dormant release/tag/Pages effects, including automatic environment deployment records. `publish.yml` uses `environment.deployment: false`; prove actual Pages behavior rather than inferring it from YAML.
- [ ] Refresh the full nonsecret before-state, key/secret consumers, repository writers and organization constraints. Retain exact settings for comparison, not as a rollback permission grant.
- [ ] Prove built-in GitHub Actions integration **15368** is eligible here for B's PR-only review bypass and the separate tag-creation bypass. Its ID or a valid API payload is insufficient. The app-level actor identifies Actions generally, not one workflow; limited trusted writers and reviewed workflow changes are part of the accepted model.
- [ ] If unsupported, retain both automatic route flags false and record the unresolved feasibility decision. Do not substitute an App, PAT, deploy-key bypass or weaker checks. Publication also stays off if its prerequisites fail.

## Stage 2: protections before automatic routes

Apply through repository Settings → Rules → Rulesets, Actions → General, Security, Releases and Environments as appropriate; export resulting API state to #43. Review the effective layered result before removing the original broad ruleset.

- [ ] **Ruleset A**, main, active, **no bypass actors**: preserve deletion/non-fast-forward restrictions; strict/up-to-date required `results` and head-specific `merge-gate` checks pinned to Actions 15368; source-commit signatures; CodeQL high-or-higher security/errors; resolved review conversations. Prove `merge-gate` is emitted on every current PR head before requiring it. Do not strand PRs by requiring a missing check.
- [ ] Include the native unresolved-secret-alert rule where supported. Otherwise explicitly retain the approved `SECRET_PATTERNS` plus GHAS push-protection fallback and document its narrower detection coverage. Security must approve the deterministic blocking set and fixtures; a nonempty configuration alone does not prove human sign-off.
- [ ] **Ruleset B**, main: one approval and CODEOWNERS review with stale-approval dismissal. Only supported Actions and Admin role bypass, both **pull_request** mode. Preserve other reviewed PR requirements (including unattributed-change review behavior where applicable). Neither actor bypasses A. Verify the combined effective rules retain conversation resolution.
- [ ] Preserve existing no-bypass `catalog-*` update/deletion/non-fast-forward controls. Add **separate creation-only** protection with the supported publisher actor. Its bypass must not reach mutation protection.
- [ ] Set default workflow permissions read-only; disable Actions PR creation/approval. Preserve least job permissions and main-only Pages. Confirm effective fork approval or document manual approval. Preserve GHAS/CodeQL; enable release immutability for future publications.
- [ ] Replace the old main ruleset/bypasses only when the complete A/B result is ready. This removes the DeployKey/Admin always bypass at the protection transition. Retain physical key/secret temporarily for staged retirement, inert against protected main/tags. If the transition cannot preserve hard controls, stop with flags off. Failure never restores an always bypass.

[GitHub ruleset semantics](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets), [source signing](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-signed-commits), [immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases) and [environment deployment controls](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments#using-environments-without-deployments) explain the provider contracts; their availability does not prove this repository's actors or settings.

## Stage 3: controlled live acceptance

For each case record actor, PR URL, exact source/head/base/merge SHAs, authenticated PR run ID/attempt/jobs, gate check and reasons, dispatch ID, release/tag/asset digest and actual Pages outcome. Distinguish missing, failed and passed. Use harmless deterministic fixtures or mocked failure conditions; never live secrets. Validate staging with flags off first. An administrator may temporarily enable a single effect/route for its controlled proof; return it off on failure. A flag change merely allowing a run is not a proof.

- [ ] Human reviewed signed merge and manual `publish.yml` reconciliation succeed under A/B. Prove tag target, uploaded/downloaded asset and Pages exact bytes plus four independent coordinates. Docs-only deployment reuses the asset; meaningful policy/owner change creates a matching snapshot.
- [ ] Release succeeds/Pages fails recovery reuses the same tag/bytes. Newer withdrawal defeats old active retry, old data replay and stale site deployment. Site-code rollback retains newest accepted data.
- [ ] Eligible signed Community **fork** merges through Community route; grouped verified Actions and uv Dependabot updates (including supported majors) through dependency route. Each bypasses only review and dispatches publication. Prove source commits meet native signing for signed local forks, browser commits and bot heads; a GitHub-signed final squash alone is insufficient.
- [ ] Specialty, non-maintainer edits, restoration and ownership transfers remain human-review. Private membership/public endpoint 404 and API errors remain distinct unconfirmed holds. A reviewed membership hold requires authoritative bcgov eligibility confirmation; confirmed outsiders fail.
- [ ] All three exact-head route outcomes (`community-auto`, `dependency-auto`, `human-review`) appear correctly; hard failures still fail with flags off. Verify historical fork association/tested head/base correlation, current attempts and stale-head suppression. Missing historical fork binding holds, never invents authorization.
- [ ] Both Admin and Actions fail to bypass A on failed required checks, approved blocking findings, stale head/base, unsigned source commits, CodeQL and selected secret enforcement. Exercise main/tag deletion/non-fast-forward protection, existing tag update/delete refusal and fresh publisher-tag creation.
- [ ] Exercise dispatch failure diagnostics, manual gate retry, publication recovery, quota boundaries and an Admin incident/sole-owner reviewed path. Record actual controls after each staged change.

## Stage 4: sustained activation and retirement

- [ ] Only independently proved routes stay enabled; failed shared prerequisites disable both. Publication stays enabled only after its own controls/proofs. Leave a non-proved route off and #7 incomplete rather than broadening policy.
- [ ] After human **and coordinator-dispatch** publication work, remove actual stored deploy-key secret(s) and repository key id 165187949, reconcile every current name/consumer and verify no legacy bypass survives. Delete unused ORG_READ_TOKEN after checking all consumers. Do not rename secrets to satisfy stale workflow references.
- [ ] Re-list key/secret metadata and effective protections; prove another publication without retired credentials. Link before/after evidence and exact outcomes in #43. No secret values belong in the record.

## Kill switches and operator retries

All flags are Admin-owned reviewed config changes. `publication.enabled: false` stops release/tag/Pages effects independently of merge routing. Each route has its own kill switch (`community-intake.auto-publish` or `dependency-intake.auto-merge`); both additionally require publication. A shared protection/authorization failure means disable both routes. During an urgent in-flight incident, an administrator can cancel affected Actions jobs while landing the false flags; inspect actual effects because a completed API effect cannot be undone by cancellation. Never force-push main, move a tag or restore a retired bypass.

The trusted gate runs API-only from latest main and reauthenticates run/attempt, repo/PR/head/base, immutable inventories, checks, membership and quota before synchronous expected-head squash merge. No proposed workflow, package code, artifact, label or title authorizes it. API limits/truncated evidence hold. Ten new identities per author in seven days includes the entire candidate batch; tombstones/restoration/transfers are not new identities. Higher risk, unavailable quota and other valid holds route to human review. Dependency authorization is separate: exact verified Dependabot identity/group metadata, trusted Actions/uv groups, limited dependency-ref/constraint changes; ambiguous changes require review. Majors are supported, not automatically approved outside those bounds. See [gate reference](docs/MERGE_GATE.md).

After a lost event, superseded completion or queue limit, rerun current PR validation, then retry only its current completed run/attempt:

```sh
gh workflow run merge-gate.yml --repo bcgov/agent-marketplace --ref main -f run-id=RUN_ID -f attempt=ATTEMPT
gh workflow run publish.yml --repo bcgov/agent-marketplace --ref main -f mode=reconcile
```

Dispatch success records an accepted workflow run, not publication success. If merge succeeded but dispatch failed/timed out, inspect existing publication runs, then reconcile current main manually. Do not re-merge or arm deferred auto-merge. The merge API has an expected-head guard but no expected-base argument; strict native current-base protections are mandatory even with the gate queue.

## Exact-revision recovery

`publish.yml` serializes attempts, fetches latest main with full history and validates/builds before effects. A meaningful change allocates `catalog-YYYY.MM.DD[.N]` in UTC, creates a matching draft/full-SHA target, uploads one `catalog.json`, downloads/verifies bytes, then publishes before Pages. Release notes/latest designation are mutable and do not establish accepted lineage. Operational enable flags are excluded from meaningful content; registry/owners, policy, declared limits, actual scan/install/authorization inputs and native choices remain meaningful. Generated CODEOWNERS is the only tracked projection; publication never commits to main.

| Failure | Supported recovery |
| --- | --- |
| Matching draft before upload | Retry reconciles and uploads once |
| Upload response lost | Download/compare and reuse; no clobber |
| Conflicting draft/tag/asset or starter asset | Stop and diagnose exact revision/bytes; never overwrite published data |
| Publish response lost | Discover accepted release and reuse |
| Release accepted, Pages fails | Reconcile same exact asset; no duplicate semantic snapshot |
| Newer snapshot accepted or current flags off | Old attempt refuses effects; reconcile current or remain off |
| API/permissions failure | Retain diagnostic and fix authorized controls; no credential fallback |

For **latest accepted asset recovery**, dispatch `-f mode=newest` on main after checking enabled controls and accepted lineage. It renders newest accepted bytes with current site code. It cannot select an old tag/source. An accepted newer withdrawal cannot be replaced by an old active Catalogue, even under a new tag. Immediate current-main/newest-data checks guard asset upload and deploy; the API provides no atomic external-config compare-and-swap guarantee.

For **site-code rollback**, revert the rendering change through a reviewed, signed PR compatible with current Catalogue schema, retain current policy/lifecycle data and dispatch `newest`. If the old renderer cannot consume current data, fix the renderer; never replay old data to make it work. For **historical inspection**, explicitly download a chosen immutable asset separately, verify its digest and label its source/snapshot/status as historical. Historical download is not a deployment or a current-status fallback.

The footer keeps site source/run/attempt, Catalogue snapshot/source/asset digest, recorded release and successful deployment evidence separate. Inspect `assets/site-build.json`, release API/tag target, downloaded `catalog.json` and successful Pages event/run. Build/run timestamps alone do not establish deployment. Source-added/updated are UTC first-parent source dates; baseline unknown additions remain null.

## Incident response

Follow [private reporting](SECURITY.md). Security triages findings; Admins disable affected effects and coordinate with content owners. Remove hard-blocked bytes directly in a reviewed signed PR, retaining a Manifest-only removed tombstone with summary/notice and the same reserved identity. Quarantine may retain only passing content. Revoke exposed credentials at their owner immediately and privately arrange platform/history/asset removal if required; normal publisher recovery never clobbers historical assets. Publish the newest withdrawal and safe native removal guidance; installed copies cannot be revoked remotely. Keep private report details out of public notices.

Restore only corrected, passing content through reviewed lifecycle changes. Community restoration needs Admin review; Specialty restoration/transfer needs relevant old/new owners. Keep the reserved identity or explicitly create a new one with a retained old tombstone; replacement chains retain all notices and never install automatically.

## Ownership and onboarding

Admins (`@bcgov/agent-marketplace-admins`) own registry, engine, workflows, general configuration and docs. Specialty teams own content under all four registered paths. Security (`@bcgov/security`) exclusively owns `config/security-policy.yaml` and `tests/security-policy/`, including deterministic pattern changes and approval of blocking rules. CODEOWNERS expresses requested ownership; it does not prove an actual review. Maintainers are contacts and trusted-base individual auto-edit inputs, not a general content ACL.

To onboard a Specialty: agree unique id/scope, active GitHub owner team, display name/description/review-rule/flair and coverage (prefer at least two members); change `config/specialties.yaml` in an Admin-reviewed PR; run `make generate`; verify generated ownership for skills/instructions/prompts/agents and both package files; validate/build; send a ready test PR and verify owner review delivery. A team rename/transfer uses reviewed old/new owner agreement and checks all affected paths. Preserve stable type/name identity, install path migration consent and any lifecycle notices.

When only one eligible owner exists, record the conflict and rationale in the PR/incident, obtain an independent qualified reviewer or documented Admin oversight, then have an Admin use **B's PR-only** reviewed path with A fully satisfied. Do not self-approve, waive Security policy approval or use a broad bypass. If review responsibility cannot be fulfilled, hold the change and arrange coverage. For an urgent takedown, Admins retain authority to remove bytes with recorded incident rationale; subsequent restoration still needs the appropriate owners. Review writer/team coverage and all three flags after personnel changes.

## Evidence preservation and cleanup

[Research archive](docs/research/README.md) records original hashes, historical limits and exact candidate refs. [Cleanup inventory](docs/research/ref-cleanup.md) distinguishes prepared preservation from retained-main proof and actual deletion. Integration sources are not retained-main preservation until merged. Update stable decision references after merge and verify every listed source/backup before deleting any obsolete ref. Preserve active user branches/worktrees, all v1 refs, tags/releases and PR refs. No blanket pruning.
