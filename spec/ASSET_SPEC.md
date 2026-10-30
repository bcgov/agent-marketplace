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
├── prompt.prompt.md
└── bcgov-extension.yaml

instructions/<community-or-specialty>/<name>/
├── instructions.instructions.md
└── bcgov-extension.yaml

agents/<community-or-specialty>/<name>/
├── agent.agent.md
└── bcgov-extension.yaml
```

Packages may include flat `assets/`, `references/`, and `scripts/` resources.
Codex-specific `agents/openai.yaml` metadata is optional and is not required
for a package to be a valid skill.

## Type-specific content

Every content file is UTF-8 Markdown with non-empty content. Types other than
skills require YAML frontmatter with a non-empty `description`.

- **Skill**: `SKILL.md`; validated by [SKILL.md Spec](./SKILL_SPEC.md).
- **Prompt**: `prompt.prompt.md`; a focused, reusable request. The `name` and
  `agent` fields are optional. A prompt's `name`, when present, is a display
  name and need not match the package name.
- **Instructions**: `instructions.instructions.md`; persistent guidance.
  `applyTo` is optional; when omitted, the host decides where the guidance
  applies. The `name` field is optional.
- **Agent**: `agent.agent.md`; a focused assistant role with explicit
  responsibility and boundaries. It requires `name` and `description`; the
  name is a display name.

## Marketplace manifest

Every manifest uses the closed
[`bcgov-extension/v1alpha1` schema](../schemas/bcgov-extension-v1alpha1.schema.json).
It records the stable extension ID, summary, publisher, maintainers, support,
license, lifecycle, prerequisites, declared capabilities, and optional
compatibility exclusions.

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
