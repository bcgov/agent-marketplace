# Getting started with the BC Gov Agent Marketplace

Browse the Catalogue or install the `bcgov-find-extension` and
`bcgov-create-extension` companion skills using their native choices. They do
not require a marketplace checkout. Find up to three relevant active records,
inspect their revision-specific checks and capabilities, then select one.

## Install a published Extension

Select an active record in the latest published Catalogue and consume its
`install-options`. Show the canonical identity, repository, source path, full
SHA, client, manual installer, scope, exact native file map, capabilities and
checks. A main-based link is latest source and may be ahead of the Catalogue;
it is never latest published or pinned. A SHA in a URL does not verify bytes.

Download the full-SHA directory. Compare file SHA-256 hashes with the
Catalogue. Inspect existing destination files, directories and symlinks; stop
on collisions. Obtain explicit confirmation, then copy only the mapped native
files and compare installed hashes. Skills preserve their full resource tree;
the other three types flatten canonical native files only where no resource
adaptation is needed. Do not copy `bcgov-extension.yaml`.

VS Code Local project choices use `.github/skills/<name>/`,
`.github/instructions/<name>.instructions.md`, `.github/prompts/<name>.prompt.md`
and `.github/agents/<name>.agent.md`. Skills also have a tested personal/global
choice under `~/.copilot/skills/<name>/`. Other global/native installer actions
are withheld. This is layout/placement evidence, not per-asset runtime testing.
See [the tested matrix](INSTALL_TEST_MATRIX.md) and [the installation guide](consume.html).

For updates, compare the old/new Catalogue maps and installed bytes, preserve
local edits, and explicitly replace only selected files. Legacy aliases resolve
lookup only; use the canonical ID explicitly. Specialty transfers preserve the
identity but require explicit approval of changed source coordinates. Never
automatically follow a moved-to pointer. Remove by explicitly deleting only
the selected revision's mapped native files and preserving unrelated guidance.
Non-active records have no install action; older affected pins need the current
notice's update/removal guidance. Keep the selected Catalogue snapshot for
later comparisons. No local tracking registry is created.

## Contribute

Use `bcgov-create-extension` or the contribution guide to create native content
and a minimal Manifest. Preview the diff and checks, then explicitly submit
a pull request. Publication and review are separate from installation.
