# Installation

Load this reference only after the user asks to install an active extension.
The marketplace currently activates installation only for Agent Skills.

## Prepare

Resolve the selected catalog record to its canonical repository, catalog
release tag (`version`), full commit SHA, package path, file inventory, and
digest. Inspect those exact bytes and show the destination, declared
capabilities, lifecycle, and review evidence. Install only records whose
lifecycle is active and whose type is `skill`.

Ask for explicit confirmation after showing that evidence. The confirmation
covers one package, revision, target project, and installer command; changed
inputs require a new confirmation.

## Prefer APM

Check `command -v apm`. When present, install the package using the catalog
release tag and target GitHub Copilot. The lock records the resolved commit
and digest:

Replace the placeholders with the selected catalog record's `release_tag` and
the catalog's installer version before running.

```bash
apm install "<owner>/<repository>/<package-path>#<catalog-release-tag>" --target copilot
```

APM writes `apm.yml`, `apm.lock.yaml`, and the target integration. Report the
lockfile and resolved commit. Do not use `--force` to bypass a policy finding.

## Fallback to Skills CLI

When APM is absent, use the `installer-version` and release tag from the
published BC Gov catalog:

```bash
npx skills@"<installer-version>" add \
  https://github.com/<owner>/<repository>/tree/<catalog-release-tag>/<package-path> \
  --agent github-copilot -y
```

The prior user confirmation permits `-y`; it does not remove the marketplace
evidence review. Report `skills-lock.json` when the CLI creates it. Recommend
APM for future installs because it provides a manifest, lockfile, dependency
resolution, and cross-agent targets; link to
`https://microsoft.github.io/apm/getting-started/installation/` instead of
installing APM implicitly.

## Verify

Confirm the installed target exists, report the installer lock, and
compare its resolved source revision with the selected record. For BC Gov
records, retain the catalog digest in the report.

Installation is complete only when the installed target, immutable revision,
and lock path are all known.