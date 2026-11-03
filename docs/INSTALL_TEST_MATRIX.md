# Native install contract evidence

The shared `build_install_choices(record, native_directory)` interface supplies
the Catalogue site and finder. `place_choice`, `verify_choice` and `remove_choice`
exercise actual native file operations without executing contributed content.
They replace the former tracking-based installation path. These are tested
layout contracts, not runtime certification of every Extension (ADR 0001).

| Type | Canonical package content | VS Code Local project destination | Additional tested scope |
| --- | --- | --- | --- |
| skill | `skills/<specialty>/<name>/SKILL.md` and resources | `.github/skills/<name>/SKILL.md` and the same resource tree | personal/global `~/.copilot/skills/<name>/` |
| instructions | `instructions/<specialty>/<name>/<name>.instructions.md` | `.github/instructions/<name>.instructions.md` | none |
| prompt | `prompts/<specialty>/<name>/<name>.prompt.md` | `.github/prompts/<name>.prompt.md` | none |
| agent | `agents/<specialty>/<name>/<name>.agent.md` | `.github/agents/<name>.agent.md` | none |

The installer is manual file placement. Native support directories remain
inside each skill. Single-file types flatten only their canonical native file;
packages needing an untested resource adaptation receive no advertised choice.
The governance Manifest is never installed. Native VS Code headers are optional
for instructions/prompts/agents, while skills require the native name and
description. GitHub agents independently require a native description: this
matrix advertises no GitHub agent option. Known incompatible native `applyTo`,
`tools` or agent `target` fields suppress the VS Code choice. Missing optional
headers do not create a universal native-description requirement.

Run `uv run pytest -q tests/test_install_choices.py` for the CI contract. It
covers all four native layouts, skill resources, full-SHA archive URL and
latest-source construction, real file copying, downloaded/installed SHA-256
comparisons, existing destinations, linked destinations, explicit canonical
legacy-alias selection, separate Specialty path migration, local-edit refusal,
explicit overwrite from a selected previous Catalogue, removal preserving
neighbors, reinstallation and non-active/moved record suppression. HTTP archive
fixtures are immutable test inputs, not claims of a live package or client run.
The default live Catalogue source comes from publication; explicit historical
snapshots support comparison/removal, and current lifecycle notices must be
checked before considering an older affected pin.

## Recorded smoke, 2026-11-03

On Windows 10 x64, Python 3.13.13, the repository helper downloaded a real
immutable GitHub archive for `bcgov-public/skill/repo-hardening`:

- Repository: `https://github.com/bcgov/agent-marketplace`
- Source SHA: `f44b09e86ed922cd09fceaf25ec3f2a49ff6a7fd`
- Source directory: `skills/security/repo-hardening`
- Project placement: `<isolated-project>/.github/skills/repo-hardening/`
- Personal/global placement: `<isolated-home>/.copilot/skills/repo-hardening/`
- Installer: manual native copy through the repository helper.
- Both scopes: immutable archive download, complete staged inventory/digest
  comparison, native choice validation, install, installed byte verification,
  existing-destination refusal, and explicitly selected previous-Catalogue
  overwrite passed. Every reported verification compares real file bytes.

The smoke constructed a source-contract Catalogue from downloaded bytes; it
did not publish or assert a new accepted Catalogue release. Both roots were
isolated directories. No live client profile, settings or authentication was
changed. `code --version` observed VS Code **1.144.0**, commit
`2c33b50b16c472efe58357d1d2a8a5414bc23fbf`. No authenticated Copilot session,
client discovery or runtime execution was performed. The four-type fixture
placement suite runs on Linux as part of `make verify`; it does not imply that
each Extension received a runtime evaluation.

## Native references

Checked 2026-11-03: [skills and personal/project directories](https://code.visualstudio.com/docs/agent-customization/agent-skills),
[instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions),
[prompts (Local sessions)](https://code.visualstudio.com/docs/agent-customization/prompt-files),
[agents and optional headers](https://code.visualstudio.com/docs/agent-customization/custom-agents),
and [GitHub agent-specific requirements](https://docs.github.com/en/copilot/reference/custom-agents-configuration).
Other clients, global non-skill paths, APM/npx commands and native deep links
are withheld until their exact layout/scope contracts are tested.
