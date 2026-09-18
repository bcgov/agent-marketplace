# Writing skills

Load this reference only when authoring or revising an Agent Skill.

## Shape the invocation

A skill is an on-demand, repeatable workflow that may bundle scripts,
references, or assets. Use an instruction for guidance that should accompany a
class of files, a prompt for one focused task, and an agent when a role needs
isolated context or restricted tools.

Write `description` as the routing pointer: lead with the capability, then name
each distinct request branch that should trigger it. Collapse synonyms for the
same branch. The body already carries the skill's identity, so spend the
description on what it does and when to load it.

For hosts that support invocation controls, keep model invocation when the
agent or another skill must discover it. Set `disable-model-invocation: true`
only for a skill intended exclusively for deliberate user invocation. BC Gov
hosted skills currently use the marketplace's closed frontmatter profile and
remain model-discoverable.

## Write the process

1. Put the ordered common path in `SKILL.md`. End every step with a checkable,
   exhaustive completion criterion.
2. Keep always-needed rules beside the workflow. Move branch-only facts,
   examples, and long procedures into flat `references/` files.
3. Make each reference link a context pointer that names the branch that
   requires it. A pointer such as "read this for OAuth callback failures" is
   stronger than "more details."
4. Co-locate a concept's definition, rules, and caveats. Remove duplicate
   explanations and environment facts that are cheaper to inspect directly.
5. Use compact leading words only when they consistently evoke the intended
   behavior. Prefer positive instructions that say what successful action
   looks like.

The result is complete when the main path works without loading unrelated
references and each alternate branch reaches one sufficient reference.

## BC Gov package profile

A submitted package uses:

```text
skills/<community-or-specialty>/<name>/
|-- SKILL.md
|-- bcgov-extension.yaml
|-- assets/       optional, flat files only
|-- references/   optional, flat files only
`-- scripts/      optional, flat files only
```

Use the hosted
[`SKILL_SPEC.md`](https://raw.githubusercontent.com/bcgov/agent-marketplace/main/spec/SKILL_SPEC.md)
and
[`bcgov-extension-v1alpha1.schema.json`](https://raw.githubusercontent.com/bcgov/agent-marketplace/main/schemas/bcgov-extension-v1alpha1.schema.json)
as the live contracts. The skill name is kebab-case and matches its directory.
Its description is at most 1024 characters and contains no angle brackets. The
body keeps the required seven sections in order and stays within 500 lines. The
manifest declares every filesystem, network, command, environment-variable,
secret-name, and data-class capability; authors omit generated review fields.

## Validation

- Exercise at least one intended trigger, one paraphrase, and one adjacent
  non-trigger.
- Follow every reference from a clean context and confirm it supplies the
  promised branch detail.
- Check the candidate against every requirement in the hosted specification and
   schema. Record anything that only protected-branch CI can prove so the user
   can distinguish local inspection from authoritative validation.