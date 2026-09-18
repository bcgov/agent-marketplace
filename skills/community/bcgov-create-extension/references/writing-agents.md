# Writing custom agents

Load this reference only when authoring a `.agent.md` role.

## Choose the boundary

Use a custom agent when the work benefits from isolated context, a focused
role, restricted tools, or an explicit handoff. Use a skill when the same agent
can perform every step, and instructions when guidance should stay in the
current conversation.

Place workspace agents under `.github/agents/<name>.agent.md`. Use focused
frontmatter:

```yaml
---
name: "Dependency Reviewer"
description: "Review dependency changes, lockfile evidence, and supply-chain risk."
tools: [read, search]
user-invocable: true
disable-model-invocation: false
---
```

## Define the role

Give the agent one responsibility, the minimum tool set, explicit input and
output contracts, and checkable stop conditions. Put trigger branches in the
description so a parent agent can delegate correctly. Keep handoffs acyclic and
state what evidence must exist before each transition. Prefer capability
boundaries such as "read-only review" over long lists of forbidden actions.

The agent is complete when it can finish its role using only declared tools,
returns the promised output, and cannot enter a circular or premature handoff.

## Marketplace status

Custom agents are reserved in the BC Gov marketplace. Produce a valid portable
draft, but do not create an `agents/` marketplace package or claim it can be
submitted or installed until the schema, scanner, and target adapter are
active.