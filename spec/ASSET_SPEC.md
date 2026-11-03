# Agent Asset Package Spec

The marketplace accepts four declarative asset types. Each package includes
one type-specific content file and a `bcgov-extension.yaml` marketplace
manifest. Hooks and MCP servers remain deferred.

## Canonical package paths

```text
skills/<community-or-specialty>/<name>/
├── SKILL.md
└── bcgov-extension.yaml

prompts/<community-or-specialty>/<name>/
├── <name>.prompt.md
└── bcgov-extension.yaml

instructions/<community-or-specialty>/<name>/
├── <name>.instructions.md
└── bcgov-extension.yaml

agents/<community-or-specialty>/<name>/
├── <name>.agent.md
└── bcgov-extension.yaml
```

Packages may include flat `assets/`, `references/`, and `scripts/` resources.
Codex-specific `agents/openai.yaml` metadata is optional and is not required
for a package to be a valid skill.

## Type-specific content

Every content file is UTF-8 Markdown with non-empty content. All four types
can supply `description` in YAML frontmatter. A missing native description
needs a Manifest `summary` for Catalogue metadata. VS Code Local accepts optional
headers for non-skill types. Native client constraints gate advertised choices
independently: skills require native name/description; GitHub agents require
a native description, so a VS Code choice must not imply GitHub compatibility.

- **Skill**: `SKILL.md`; validated by [SKILL.md Spec](./SKILL_SPEC.md).
- **Prompt**: `<name>.prompt.md`; a focused, reusable request. The `name` and
  `agent` fields are optional. A prompt's `name`, when present, is a display
  name and need not match the package name.
- **Instructions**: `<name>.instructions.md`; persistent guidance.
  `applyTo` is optional; when omitted, the host decides where the guidance
  applies. The `name` field is optional.
- **Agent**: `<name>.agent.md`; a focused assistant role with explicit
  responsibility and boundaries. Its optional frontmatter `name` is a
  display name in VS Code Local.

## Marketplace manifest

Every manifest uses the closed
[`bcgov-extension/v1alpha1` schema](../schemas/bcgov-extension-v1alpha1.schema.json).
Only `maintainers` and `capabilities` are required; `capabilities: none` is an
explicit declaration of no access. The catalog derives `id`, `type`,
`specialty`, and `name` from the directory. `display-name` comes from the
Manifest, then frontmatter `name`, then the directory name verbatim. `summary`
comes from the Manifest, then frontmatter `description`; there is no body
fallback. Effective display names are non-blank strings up to 80 characters;
effective summaries are non-blank strings up to 1,024 characters through either
source. Native constraints (including the skill format) still apply.
The catalog uses `bcgov-marketplace/v1`, with `checks`, declared `risk`, and
`policy-route` evidence; the former `policy`, `review`, and `route` aliases
are retired. Unknown human-review evidence is not inferred from CODEOWNERS.

Identity is `bcgov-public/<type>/<name>`, where type is `skill`, `instructions`,
`prompt`, or `agent`. Names are unique within each type across all Specialties.
Identity fields cannot be overridden in the Manifest. A Specialty-only transfer
preserves identity and requires reviewed ownership transfer. Published pre-v1
name-only IDs are inventoried in Admin-owned `config/legacy-ids.json`, from the
immutable `catalog-2026.10.01` asset (SHA-256
`f2376c9b0102ea128fac4205ba6387f926b596dfe506d77c65d497be12b11b5a`).
Only those explicit aliases resolve in the current Catalogue; historical
snapshots retain their original IDs. This mapping is a finite migration list,
not a registry for new identities or a heuristic name lookup.

The default lifecycle is `active`. Set `lifecycle: quarantined` with `notice`
to keep content visible with a warning but block installation. Set
`lifecycle: removed` with `notice` and remove all content, leaving only the
Manifest (including `summary`) as a tombstone. A name/type change creates a
distinct identity: retain the old removed Manifest with
`moved-to: bcgov-public/<type>/<new-name>`. This pointer is allowed only on a
non-active record. Targets must exist; self-pointers and cycles fail validation.
Finite chains may end in active, quarantined or removed records; the Catalogue
reports the terminal lifecycle without automatic migration. Non-active records
remain published but offer no install actions. Quarantine retains only content
that passes the same approved checks as active content; hard-blocked bytes must
be fixed or directly removed.

`marketplace.py validate --base <trusted-sha>` also checks every trusted-base
identity and both sides of every changed content path. Every non-draft identity
on trusted main stays reserved, including before publication. Retirement needs
a retained non-active Manifest; validation never synthesizes contributor files.
`analyze <package> --base <trusted-sha>` exposes the same transition facts for
the trusted merge gate: lifecycle/notice/redirect changes, non-active content,
restoration, identity replacement and Specialty transfer require human review,
while remaining valid format changes. Facts include old/new Specialties and
trusted-base maintainers. Admins retain takedown authority; Community restoration
needs Admin review, and Specialty restoration/transfer needs the relevant owners.

`compatibility.not-ready-on` is a unique list of lower-case harness identifiers
such as `github-copilot-vscode`, `claude-code`, or `openai-codex`. It records
author-declared exclusions only. An absent or empty list means no exclusion
was declared; it does not mean the asset was runtime-tested or is known to work
in any particular harness.

## Harness compatibility

The marketplace validates package shape and metadata, not runtime behavior or
model quality. A supported format may be interpreted or installed differently
by different harnesses. Authors should list harnesses where an asset is not
ready and provide native import guidance. The catalog displays these
author-declared exclusions without turning them into a compatibility
certification.

The Agent Skills format is supported by multiple products, but the other asset
types do not share one universal native format. For example, GitHub Copilot
uses `.prompt.md`, `.instructions.md`, and `.agent.md` files, while Codex
custom agents use TOML and Claude Code custom agents use Markdown with
frontmatter. Use the links below for current host requirements:

- [GitHub Copilot prompt files](https://docs.github.com/en/copilot/concepts/prompting-and-context/prompt-files)
- [GitHub Copilot repository instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)
- [GitHub Copilot custom agents](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli)
- [OpenAI Codex skills](https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/skill-creator)
- [OpenAI Codex custom agents](https://github.com/openai/codex/blob/main/codex-rs/agent-roles/src/loader.rs)
- [Claude Code custom agents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)

The initial pilot smoke-tests the marketplace workflow on Copilot CLI, VS Code,
and Copilot app. These tests do not establish per-asset compatibility.
