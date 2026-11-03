# Catalogue publication and recovery

The single `publish.yml` workflow runs on main pushes and manual dispatch. Its
shared concurrency group does not cancel an active attempt. Queued attempts
explicitly fetch and select latest main, with full history; intermediate source
states may be coalesced. `reconcile` compares latest source with the accepted
release chain. `newest` renders the newest accepted Catalogue around current
site code. Dispatch offers no old tag, asset, or historical source input.

`publication.enabled` is an Admin-owned, default-off control independent of
Community and dependency merge routes. Disabled runs validate and build but
perform no release, tag or Pages mutations, including the first workflow merge.
The release adapter fetches the switch from current main immediately before
each mutation; upload and deploy steps recheck it again. Historical config cannot
enable recovery. Activation and the live control/credential/actor proofs belong
to #43; this implementation does not perform them.

Meaningful comparison includes effective metadata, package inventory/digests,
lifecycle/notices/replacements, findings, policy and actual engine input identity,
Specialty registry ownership/flair, approved discovery sources and install
client/layout/placements. Only generated snapshot source pins and per-choice
source URLs are normalized. Authored SHA-bearing values, installed file hashes,
adapter behavior and policy are retained. Engine identity hashes the executed
validators/install adapter and trusted schema/policy inputs; it is independent
of repository HEAD and publication controls.

The explicit baseline in `config/publication-baseline.json` authenticates the
legacy `catalog-2026.10.01` asset by its schema, nine identities, digest, tag
target and distinct embedded source SHA. The first v1 asset records that
transition and its finite aliases. Every later asset records its predecessor tag
and digest. Missing, malformed, forked or unreadable history fails; it never
becomes an implicit first publication. Mutable release notes and the REST
`latest` endpoint are not acceptance authority.

For a meaningful change the coordinator allocates the next free UTC
`catalog-YYYY.MM.DD[.N]` against remote refs, releases and drafts. It builds and
validates the staged site before creating a draft targeted at the selected full
source SHA, uploads one `catalog.json`, downloads/checks its exact bytes and
publishes. It resolves actual tag targets independently of `target_commitish`.
Published tags/assets are never updated or deleted. Pages receives those exact
immutable bytes. Docs-only attempts retain the original source SHA and tag.

| Failure/state | Next attempt |
| --- | --- |
| Draft created, upload not accepted | Resume that matching draft and upload once |
| Upload accepted but response lost | Download, compare and reuse; no overwrite |
| Draft contains different bytes/SHA | Fail with diagnostics; never clobber |
| Empty or `starter` asset | Stop for operator diagnosis; no automated deletion |
| Publish accepted but response lost | Discover accepted release; reuse its tag/asset |
| Release published, Pages failed | Reuse exact bytes; do not allocate another tag |
| Newer accepted release arrived | Refuse old deploy/retry; reconcile latest or `newest` |
| Current main disables publication | Stop remaining effects, including recovery |
| Workflow-permission/API error | Keep failed run and diagnostics; no credential fallback |

The workflow guards both Pages artifact upload and deployment against disable
and supersession. The GitHub APIs cannot make an external config check atomic
with a subsequent mutation; immediate rechecks and shared workflow serialization
reduce that race but do not claim a server-side compare-and-swap guarantee.

Four coordinates remain separate: package repository/path/full source SHA;
Catalogue tag and externally computed asset digest; site source/run/attempt in
`assets/site-build.json`; and actual release/deployment records. The footer
shows snapshot/site coordinates and actual release publication time when known.
Successful deployment evidence lives in the Pages deployment and successful
workflow step/run, not an asset's build timestamp. An asset never embeds its own
hash, and installs introduce no local receipts.

Source `added`/`updated` values use UTC committer timestamps from first-parent
history strictly after `history-start`. Identities present at that baseline have
unknown (`null`) addition dates. Later package/path/Manifest changes update the
source date. Specialty transfers preserve type/name identity; real name/type
changes create a new identity. Invalid or unreachable baselines fail validation.
These are source dates, not first-publication claims.

Historical assets stay downloadable for explicit inspection/pinned use. They
cannot be restored silently as current data. Rolling back site rendering keeps
the newest accepted Catalogue and must satisfy its schema contract. Current
lifecycle and evidence changes use normal reviewed source publication.

PR CI and `make verify` build in isolated output directories. Only authored
inputs and generated CODEOWNERS remain tracked. Consumers load the live
[Pages Catalogue](https://bcgov.github.io/agent-marketplace/assets/catalog.json).
There is no weekly publication cron, failure issue, deploy key, configuration
stamping, digest sidecar, or commit/push to main in the publication path.
