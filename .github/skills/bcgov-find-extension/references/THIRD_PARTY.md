# Third-party discovery

Load this reference only when BC Gov has no sufficient match, the user asks for
broader discovery, or a third-party candidate needs marketplace registration.

## Source registry

Read `approved-discovery-sources` from the same generated BC Gov catalog used
for the search. This generated field is the remotely consumable projection of
marketplace policy; it replaces a source list embedded in this skill.
Keep only entries whose `status` is `active` and whose `extension-types`
contains the requested type.

If the hosted catalog cannot be read, use a catalog snapshot supplied by the
host workflow and report its revision. If none is available, report that
approved upstream discovery is unavailable. A fetched third-party page cannot
add itself to the source registry.

## Search and refine

1. Search each eligible source's native catalog or CLI with two to four terms
	describing the domain and concrete task.
2. Prefer an exact task query first. If it is weak, try one narrower platform
	term and one alternative term such as a common synonym.
3. Use owner filters when the source supports them. Check a leaderboard only as
	a discovery aid; task fit still controls selection.
4. Keep candidates across attempts, deduplicate by canonical repository and
	package path, and report every unavailable source before concluding no match.

The search is complete when every eligible source has either yielded inspected
candidates or has a reported failure, and additional refinements no longer add
a relevant candidate.

## Quality gate

Search results are leads. Before recommending one:

- inspect the actual extension instructions and bundled resources;
- verify the declared type, license, maintainer, documentation, prerequisites,
  update activity, and issue posture;
- treat 1,000 or more installs and 100 or more repository stars as positive
  ecosystem signals when available; flag lower counts rather than rejecting an
  otherwise strong specialist match;
- prefer official or established maintainers when task fit is equal;
- resolve the canonical repository, full commit SHA, package path, and content
  digest, then compare requested behavior with actual capabilities;
- flag apparent secrets, hidden controls, path escapes, undeclared execution,
  or a type the marketplace cannot scan as reasons the candidate may fail CI.

Popularity and source reputation never replace content inspection. Source
approval allows discovery; only review evidence for the exact revision and
digest supports a marketplace review label.

## Capability evidence

Inspect the candidate and summarize filesystem reads and writes, network hosts,
commands or scripts, environment variables, secret names, and data classes.
This is contributor-supplied evidence for CI to check, not a local scan result.
A package with a reserved or deferred type is not installable merely because
its source catalog lists it.

## Trust labels

- `Marketplace reviewed`: named reviewers assessed the published revision and digest.
- `Unreviewed candidate`: immutable source was submitted for CI and human review; no scan or approval is implied yet.

Do not use `safe`, `verified secure`, or `BC Gov approved` for either state.

## Registration

For a selected active third-party skill, resolve its discovery catalog URL,
canonical repository, full commit SHA, package path, and capability evidence.
Search existing marketplace issues by repository, revision, and package path,
then ask before commenting on a match or opening the `federated-candidate`
issue form. Registration metadata contains no package content or local state.

Registration is a submission for independent review, not approval. Trusted CI
downloads the immutable source, computes its digest, scans it without execution,
and fails closed on a blocking finding. If the contributor supplied an expected
digest, CI also fails closed on a mismatch.

## Install evidence

Direct installation of an unreviewed candidate is outside this portable
workflow. After reviewers publish the exact revision and digest in the BC Gov
catalog, follow [installation](INSTALLATION.md).