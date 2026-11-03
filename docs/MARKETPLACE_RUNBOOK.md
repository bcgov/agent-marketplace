# Marketplace operations runbook

## Ownership and support

Marketplace controls, catalog publication, and incident coordination are owned by `@mishraomp` and `@DerekRoberts`. Package maintainers named in `bcgov-extension.yaml` own domain review and user support. General requests use [GitHub issues](https://github.com/bcgov/agent-marketplace/issues); suspected vulnerabilities use the private route in [SECURITY.md](../SECURITY.md).

Acknowledge critical security reports within one business day and ordinary marketplace support within three business days.

## Access

Contributors need permission to push an in-repository branch, must use signed
commits, and must be members of the GitHub `bcgov` organization. Membership is
the contributor-eligibility proxy, not employment verification. Fork pull
requests fail closed. If access is missing, retain the validated isolated
checkout and request contributor access through a support issue. Do not move
unpublished package content to a public fork.

The `Community intake / intake` check must be required by the protected-branch
ruleset for changes under `skills/`, `prompts/`, `instructions/`, and `agents/`.
Configure `ORG_READ_TOKEN` as a repository or organization Actions secret with
the membership-read permissions documented in
[COMMUNITY_INTAKE_POLICY.md](COMMUNITY_INTAKE_POLICY.md). Without the required
status check, the workflow may report failure without preventing a merge.

## Publish

The implementation remains dormant: `publication.enabled` in
`config/marketplace.yaml` defaults to false. Only #43's human-owned control
procedure may activate it after the live actor, immutable release, Pages,
credentials and protected-branch proofs pass. No merge-route flag or release
label substitutes for that switch.

Validate and merge authored source through protected main. `publish.yml`
resolves latest main after queueing, builds in isolation, and compares meaningful
Catalogue data against validated publication history. It publishes a new
immutable `catalog.json` only when package, lifecycle, metadata, install support,
policy/engine findings or Specialty ownership/flair changes. Docs-only changes
reuse the previous asset byte-for-byte. The workflow never stamps configuration,
commits generated files, or pushes main. See [publication.md](publication.md).

## Federated candidate review

The candidate issue identifies an approved discovery source, full commit SHA, package path, and expected digest. The candidate rescan workflow independently downloads and scans those bytes. Digest mismatch or any blocking finding fails closed. Never execute candidate scripts during validation. Human reviewers decide whether to host, federate, reject, or request changes.

## Quarantine

1. Change the package manifest lifecycle to `quarantined` and regenerate the catalog. Default finder search excludes it immediately after publication.
2. Open a private security report when sensitive evidence is involved; otherwise link a public tracking issue.
3. Search repository declarations for the package ID. Ask affected teams to run finder receipt verification locally; receipts are not centrally collected.
4. Publish removal or update guidance with the affected source revision and digest.
5. Do not transfer prior review evidence to replacement bytes.

## Removal

Set lifecycle to `removed`, regenerate, and publish. Keep enough catalog and issue history to identify the old source and digest. Guidance must name the finder removal action or exact installed destination and preserve receipts until incident response is complete.

## Site rollback and publication recovery

A site-rendering rollback must keep the newest accepted Catalogue bytes and
support its schema. Use the manual `Publish Catalogue and site` workflow in
`newest` mode on main. Recovery rechecks current main's publication switch and
the newest accepted snapshot before deployment. An old failed-deploy retry
cannot restore a superseded active entry after a withdrawal.

Historical release assets remain downloadable for inspection and explicit
pinned use; they are not current recovery inputs. Lifecycle/evidence changes
require normal reviewed source changes and a new publication. Never move a tag,
replace a published asset, or restore an old Catalogue as the current one.

## Recovery checks

Confirm source validation and CODEOWNERS drift checks pass, Pages serves the
exact accepted release asset at `assets/catalog.json`, and non-active records
have no install choices. Release `published_at` and successful Pages run/deploy
records are actual event evidence. Site build time and source addition dates
are not publication timestamps. Follow the failure table in
[publication.md](publication.md); a failed history comparison is an error.
