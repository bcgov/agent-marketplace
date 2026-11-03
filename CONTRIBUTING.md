# Contributing

Use the [Contribute guide](https://bcgov.github.io/agent-marketplace/contribute.html) for the portable creator skill, local PR and two-file browser/fork journeys. [Install](https://bcgov.github.io/agent-marketplace/install.html) describes native choices; [Reference](https://bcgov.github.io/agent-marketplace/reference.html) describes formats, Manifest and lifecycle. Maintainers are contacts, not mandatory approvers. Specialty ownership and Security policy review are separate responsibilities.

## Local package changes

Fork the repository, branch from current main and add the native file plus `bcgov-extension.yaml` at the canonical type/Specialty/name path. Search existing Extensions before creating one. Use an unused stable type/name; removed identities remain reserved. Declare actual access without secrets, and include a useful task example. The browser starter can generate the same minimal files without local tooling.

```sh
uv run python scripts/create_extension.py init --marketplace . --name example --extension-type skill --description "Describe when to use this skill." --display-name "Example" --summary "Describe its useful task." --maintainer @YOUR_LOGIN
uv run python scripts/create_extension.py preview --marketplace . --name example
uv run python scripts/marketplace.py analyze skills/community/example
uv run python scripts/marketplace.py validate
```

`preview` validates and displays the public diff. Review every file before staging. The companion's `submit` command requires explicit confirmation and opens a draft PR; it does not establish eligibility or bypass required checks. For a manual PR, sign every local source commit using your established Git signing setup (`git commit -S`), push your fork branch and target upstream main. Inspect every commit's Verified status on GitHub. If an unsigned local series fails protection, preserve a backup branch, sign/rewrite only your own unpublished or agreed PR series, and update only that PR branch with an exact lease. Do not assume the final signed squash fixes unsigned source commits. Browser-created commits are GitHub-signed but still require live acceptance under #43.

Read exact-head checks and route reasons. Format/security failures need correction. Public/private membership ambiguity, Specialty changes, non-maintainer edits, lifecycle changes or unavailable quota can hold for human review. Ask an upstream maintainer to approve an awaiting fork workflow under current policy. Automatic merge/publication switches remain off until #43 acceptance; green preview checks do not activate them. Mark a draft ready only after checking both files and requesting the relevant owners.

## Development and builds

Supported verification uses Linux, Python 3.12+, uv, Node.js and Bash/Make. Native Windows has known POSIX path/mode fixture differences. Install dependencies with `make setup`; `make verify` runs formatting/lint, all tests, native and marketplace validation, ownership drift and an isolated site build with internal-link checks. Use `make format` for Python formatting.

```sh
make verify
bash docs/build.sh /tmp/marketplace-site
uv run python scripts/check_links.py .
uv run python scripts/check_links.py /tmp/marketplace-site --site
uv run python -m http.server --directory /tmp/marketplace-site 8000
```

Authored site sources are `docs/_pages`, `docs/_partials` and `docs/assets`. Catalogue and the three guides are built from those sources. Generated Catalogue assets, root HTML, cards, search and contribution metadata stay untracked. `make docs` builds a local preview in `docs`; `make serve` serves that output. Default tests never execute contributed package content. Preserve the shared Catalogue renderer and native install choices when editing presentation. A view-only change must retain exact accepted Catalogue bytes and evidence identities.

`make generate` regenerates committed CODEOWNERS from the Specialty registry; inspect that diff. Admins review tooling/configuration/docs, Specialty owners review their packages, and Security reviews blocking policy plus its fixtures. See [Operations ownership](OPERATIONS.md#ownership-and-onboarding), [quality examples](docs/EXTENSION_QUALITY.md), [placement evidence](docs/INSTALL_TEST_MATRIX.md) and [merge-gate internals](docs/MERGE_GATE.md).
