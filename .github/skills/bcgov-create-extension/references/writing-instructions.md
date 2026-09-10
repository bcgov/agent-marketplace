# Writing instructions

Load this reference only when authoring persistent or file-specific agent
instructions.

## Choose scope

- Use `.github/copilot-instructions.md` or `AGENTS.md` for concise workspace
  guidance that should affect most work.
- Use `.github/instructions/<name>.instructions.md` for a focused concern that
  is discovered from its description or attached to matching files.
- Use a skill instead when the agent should run an on-demand multi-step
  workflow with bundled resources.

For file instructions, use focused frontmatter:

```yaml
---
description: "Use when writing database migrations or schema changes."
applyTo: "db/migrations/**"
---
```

Omit `applyTo` for discovery-only instructions. Use a narrow glob when file
matching is intended; `"**"` is reserved for genuinely universal guidance.

## Write the guidance

Group each concern with its rationale, examples, and exceptions. State the
desired behavior directly and make broad requirements exhaustive, such as
"account for every changed schema." Link to live configuration instead of
copying values that can drift. Split files by independent trigger or file
scope, not merely by heading.

The result is complete when every rule is actionable, conflicts are resolved,
the description names each on-demand trigger branch, and `applyTo` matches only
the intended files.

## Marketplace status

Instructions are reserved in the BC Gov marketplace. Produce a valid portable
draft, but do not create an `instructions/` marketplace package or claim it can
be submitted or installed until the schema, scanner, and target adapter are
active.