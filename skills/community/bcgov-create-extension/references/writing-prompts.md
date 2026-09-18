# Writing prompts

Load this reference only when authoring a reusable `.prompt.md` task.

## Choose and shape the task

A prompt performs one focused task with user-supplied context. Use a skill for
a branching workflow with bundled resources, instructions for persistent
guidance, and an agent for an isolated role with restricted tools.

Place workspace prompts under `.github/prompts/<name>.prompt.md`. Use concise
frontmatter and include only fields the task needs:

```yaml
---
name: "Review Migration"
description: "Review a selected database migration for rollback and data-loss risks."
argument-hint: "Migration file or change"
agent: "agent"
tools: [read, search]
---
```

Write the body as one bounded request. Name required inputs, the evidence the
agent must inspect, completion criteria, and the output shape. Reference shared
instructions rather than copying them. Keep tools minimal and omit model or
agent overrides unless the task requires them.

The prompt is complete when one invocation has one unambiguous deliverable,
missing inputs produce a useful question, and representative output matches the
declared shape.

## Marketplace status

Prompts are reserved in the BC Gov marketplace. Produce a valid portable draft,
but do not create a `prompts/` marketplace package or claim it can be submitted
or installed until the schema, scanner, and target adapter are active.