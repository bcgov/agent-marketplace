# Marketplace operations runbook

## Ownership and support

Marketplace controls, catalog publication, and incident coordination are owned by `@mishraomp` and `@DerekRoberts`. Package maintainers named in `bcgov-extension.yaml` own domain review and user support. General requests use [GitHub issues](https://github.com/bcgov/agent-marketplace/issues); suspected vulnerabilities use the private route in [SECURITY.md](../SECURITY.md).

Acknowledge critical security reports within one business day and ordinary marketplace support within three business days.

## Access

Contributors need permission to push an in-repository branch and must use signed commits. Fork pull requests fail closed. If access is missing, retain the validated isolated checkout and request contributor access through a support issue. Do not move unpublished package content to a public fork.

## Publish

1. Confirm `make verify` passes without executing contributed package scripts.
2. Confirm the package manifest, file inventory, capabilities, policy output, upstream evidence, and generated catalog changes are present in the PR.
3. Require CODEOWNER and package-domain approval on the exact head revision.
4. Merge through the protected `main` branch.
5. For a marketplace release, update `config/marketplace.yaml` to the immutable implementation commit, set `release-state: published`, regenerate projections, rerun `make verify`, and merge that release PR.
6. Record tool versions, policy version, source commit, catalog/package digests, fixture results, pilot evidence, ruleset evidence, and named owners in the release PR.

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

## Rollback

Revert the catalog and hosted package to the last reviewed immutable revision through a signed pull request. Regenerate all projections atomically and run `make verify`. Do not force-push, move a release tag, edit generated cards by hand, or relabel changed bytes with old evidence.

## Recovery checks

Verify catalog count and IDs match manifests, generated outputs have no drift, Pages exposes `assets/catalog.json`, both companion names appear in the pinned installer list, quarantined entries are absent from default finder results, and candidate scanning still blocks every adversarial fixture.
