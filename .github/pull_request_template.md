<!--
  Thanks for contributing a skill! Fill in the sections below so reviewers can
  evaluate quickly. Delete any section that doesn't apply.
-->

## What this PR changes

<!-- One or two sentences. Link the skill: skills/<bucket>/<name>/SKILL.md -->

## Why

<!-- Who needs this and what problem does it solve? When should an agent fire it? -->

## Upstream search and provenance

<!-- Link equivalent searches. For federated content, give repository, full commit SHA, package path, digest, and license. -->

## Capabilities and review evidence

<!-- Summarize filesystem, network, command, environment, secret-name, and data-class capabilities. Human review fields are generated, never authored. -->

## Checklist

- [ ] Followed [spec/SKILL_SPEC.md](../spec/SKILL_SPEC.md) (7 sections, ≤500 lines, kebab-case name, flat resource dirs).
- [ ] Added or updated `bcgov-extension.yaml` and declared every material capability.
- [ ] Updated `SKILL.md` when behaviour changed (description, Use When, Workflow, Examples).
- [ ] Ran `make verify` locally and it passed without executing contributed package scripts.
- [ ] Confirmed no secrets, tokens, or credentials are committed.
- [ ] Reviewed the exact head revision and generated package digest shown by CI.

## Notes for reviewers

<!-- Anything reviewers should know: tradeoffs, alternatives considered, follow-ups. -->
