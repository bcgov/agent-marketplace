# Merge gate operations

`merge-gate.yml` runs from trusted `main` after the numeric PR workflow
`365544835` (`.github/workflows/pr.yml`) completes. Manual retry takes only its
run ID and attempt; GitHub metadata supplies the PR identity. The gate posts a
`merge-gate` check on the explicit current PR head and one head-specific comment.
The check title is `community-auto`, `dependency-auto` or `human-review`. Valid
review holds pass this routing check; actual validation failures fail it even
when all automation is disabled. A superseded head/run cannot write diagnostics
against a newer revision.

The privileged job checks out only `main`, installs its frozen runtime without
caches, and reads proposed trees/blobs using GitHub APIs. Package content remains
inert data in a temporary directory. Trusted-base schemas, Security policy and
the existing package analyzer validate complete resulting affected inventories,
including unchanged resources and deletions. Proposed validator/policy code,
artifacts, labels and titles cannot authorize an automatic merge. The same pure
transition comparison serves PR validation and this gate.

Three independent admin controls default off in `config/marketplace.yaml`:

- `publication.enabled`
- `community-intake.auto-publish`
- `dependency-intake.auto-merge`

Both automatic routes require publication enabled. Community also requires the
approved Security blocker set, public bcgov membership (HTTP 204), Community-only
eligible packages, declared risk at most elevated, individual author membership
in every edited package's base contacts, and the seven-day new-identity budget
(at most ten including the candidate batch). Teams remain contacts; a new head
contact grants no automatic edit eligibility. A longer window/lower ceiling is
permitted as conservative policy. No account-age or open-PR restriction exists.

HTTP 404 does not distinguish a private member from an outsider. HTTP 403, rate
limits and network failures are distinct unconfirmed holds. Admin-reviewed
membership holds need authoritative bcgov eligibility confirmation. The built-in
token and public membership endpoint need no organization-read secret.

Lifecycle/notice/redirect changes, non-active content, restorations, replacements
and Specialty transfers need human review. Community restoration is admin-owned;
Specialty restoration/transfer needs the relevant old/new owners. Base contacts
are mentioned for edits. A retained trusted-base identity cannot be deleted,
including an unpublished tombstone. Maintainers are contacts and automatic-edit
inputs, rather than mandatory PR approvers.

The dependency route separately authenticates the bot's numeric identity, exact
verified head commit, signed group metadata and trusted Dependabot configuration.
Only grouped GitHub Actions and uv updates qualify, including majors. Workflow
comparison uses strict YAML with unique keys, no aliases and GitHub boolean
spelling; only dependency refs can change while action owner/path, triggers,
permissions, commands and all other structures remain equal. uv manifest changes
are limited to dependency constraints; locks retain supported registry sources.
Unsupported or ambiguous dependency changes remain reviewable.

One repository-wide queue serializes final re-evaluation, rolling author quota
and guarded merge. The quota uses fully paginated closed PR facts, merged PR
author and merge time, and canonical inventories before/after the actual merge's
first parent, including squash merges. Missing/capped history holds. Immediately
before effects, the gate re-fetches current head/base, controls, policy and
eligibility. Synchronous squash merge supplies the exact authorized `sha`; no
deferred native auto-merge is armed. Native strict current-base checks and all
no-bypass hard protections, including source-commit signatures, must remain
enforced. GitHub's merge API has no expected-base argument; manual merges outside
the queue still require those strict native protections.

After a confirmed merge, the gate dispatches `publish.yml` on `main` with mode
`reconcile`. The diagnostic records the dispatch run ID, separately from actual
publication success. If dispatch fails or times out, inspect Actions, then
manually run `publish.yml` in reconcile mode; the publisher safely reconciles
current main. Repeated successful gate deliveries do not merge/dispatch again.
For superseded completions, rerun current PR validation or manually dispatch the
gate with the current completed run/attempt. Queue limits still require manual
retry if an event was not retained.

Historical attempt associations bind the tested PR head and base. The trusted
workflow's default checkout semantics map that pair to test-merge parents; run
and job `head_sha` are PR heads, not test-merge SHAs. A missing fork association
can be resolved through authoritative commit-associated PR metadata for a current
head diagnostic, but missing historical tested-base evidence remains a hold.
Truncated trees, ambiguous paths, incomplete pages, missing jobs or misbound
provider facts also hold. No PR-produced artifact is consumed.

Implementation tests use mocked external API responses and cannot prove live
fork provenance, native review-only actor bypass, signatures, strict-base races,
bot merges, dispatch or publication. Administrator issue #43 owns those positive
and negative activation proofs and actual legacy secret deletion. Keep all three
controls off until their shared and route-specific proofs pass. The legacy
Community and Dependabot auto-merge workflows are removed together.

API contracts: [run attempts](https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run-attempt),
[attempt jobs](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run-attempt),
[immutable trees](https://docs.github.com/en/rest/git/trees#get-a-tree),
[public membership](https://docs.github.com/en/rest/orgs/members#check-public-organization-membership-for-a-user),
[guarded merge](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request),
[dispatch response](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event),
and [Dependabot verification/metadata source](https://github.com/dependabot/fetch-metadata/tree/main/src/dependabot).
