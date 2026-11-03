# Marketplace reference

This is the reference document for the repository and the marketplace mechanics. It is organized around the actual contracts and operational boundaries of this codebase.

## Repository layout

```text
config/marketplace.yaml               centrally controlled release and source policy
config/security-policy.yaml           Security-owned scan dispositions and secret patterns
schemas/                              marketplace metadata schemas
skills/<bucket>/<name>/SKILL.md      Agent Skill content
prompts/<bucket>/<name>/<name>.prompt.md  prompt content
instructions/<bucket>/<name>/<name>.instructions.md  instruction content
agents/<bucket>/<name>/<name>.agent.md  agent definition
<type>/<bucket>/<name>/bcgov-extension.yaml  author-controlled package metadata
scripts/marketplace.py                validation, scanning, digesting, and generation
catalog/catalog.json                 generated machine-readable catalog
docs/                                public website source and generated pages
spec/SKILL_SPEC.md                   authoritative skill specification
```

## Supported asset types

The public catalog accepts skills, prompts, instructions, and agent
definitions. Each package has one canonical content file and a common
`bcgov-extension.yaml` manifest; a removed package has only its Manifest.
See [ASSET_SPEC.md](../spec/ASSET_SPEC.md).
The installer currently automates skills only. The other asset types require
explicit manual import using the target harness's native format.

The catalog's `not-ready-on` values are author-declared exclusions, not runtime
test results. An absent list does not certify compatibility.

Contributors must be members of the GitHub `bcgov` organization. This is the
marketplace's eligibility proxy, not employment verification.

## Lifecycle and review model

Each package lives under a review and lifecycle model:

- `active` — available through default discovery;
- `quarantined` — content stays available for inspection, but installation is blocked;
- `removed` — content is deleted and a Manifest-only tombstone remains;
- `moved-to` is a pointer on a non-active record, not a lifecycle state. Finite
  replacement chains may terminate in any lifecycle; installs remain blocked
  for quarantined/removed terminals and no automatic migration occurs.

Non-active records require a `notice`, remain accessible by direct lookup and
cannot be installed. A Specialty-only transfer preserves the canonical
`bcgov-public/<type>/<name>` identity. A name/type change retains an old removed
Manifest pointing to the distinct replacement identity. Every trusted-main
identity stays reserved even before publication. See the asset spec for the
finite legacy-ID mapping and trusted-base transition analysis.

Review is attached to the exact immutable source revision. Changed bytes invalidate prior review evidence.

## Trust properties

The marketplace minimizes trust assumptions by requiring:

- immutable source identity;
- deterministic packaging and digesting;
- explicit capability declaration;
- policy findings from reviewed validation;
- signed repository-backed workflows;
- human approval on the exact published revision.

It does not assume that a record is safe because it is public or because it came from a trusted authoring source alone.

## Validation and generation

The repository validation path treats contributed package files as data and does not execute them. It checks:

- layout and naming;
- metadata schema requirements;
- policy and scanner findings;
- generated output parity;
- docs and public site drift;
- the canonical repo state for the published release.

The `make verify` command is the repository’s launch gate.

### Security policy check

`uv run python scripts/marketplace.py check` scans Extension files as data and
groups blocking and advisory findings in the output and, in CI, the GitHub job
summary. Blocking findings fail the check; advisory-only findings do not. Each
finding records its rule ID, category, severity, disposition, file, line,
field, remediation and Security policy version. The same records are stored in
the catalogue's `extensions[].checks.findings` for published Extensions.
Capability risk is derived from declared Manifest capabilities only;
undeclared use is reported by the `undeclared-*` rules instead.

Security owns `config/security-policy.yaml` and the fixtures in
`tests/security-policy/`. Only rule IDs in `blocking` are approved security
blockers; removing all approved IDs is valid and leaves detected security
findings advisory. Other package-format and filesystem safety checks still
enforce their existing validation constraints. Unknown rule IDs and malformed
patterns fail policy validation. Increment `policy-version` whenever Security
changes the policy, and run `make verify` before merging. The PR workflow runs
the Security fixtures and the read-only, secret-free policy check, including
for fork contributions. This check is not a scanner pilot or a safety
certification, and it does not change the Community auto-publish default.

The `scan`, `analyze`, and demo command-line JSON is a deliberately limited
public projection of the internal scan: outcome, fixed rule identifiers and
remediation, safe file labels and line numbers (and analysis classification and
declared risk). Arbitrary Manifest values, filenames, matched content and
validation error details are not printed to terminal logs. The full internal
finding contract remains available to the catalogue build and trusted callers.

## Commands used by maintainers

```bash
make setup
make generate
make verify
make docs
make serve
```

This is the operational baseline for maintainers and reviewers. The same validation flow is used to confirm that the catalog, metadata, and public docs are still in agreement.

## Security and operations

Marketplace owners and reviewers should use the repository’s formal reporting and runbook paths, including:

- the private security advisory route;
- the operations runbook for quarantine, recovery, and rollback;
- the source-controlled publication flow for exact-review release changes.

## Quick summary

The marketplace is a repository-backed, evidence-first discovery layer for trusted agent extensions. Skills are the first publicly active implementation, but the design scope is broader than a skill-only registry and the trust model is intentionally shaped to support additional extension types under the same governance model.
