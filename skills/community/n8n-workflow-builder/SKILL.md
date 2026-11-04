---
name: n8n-workflow-builder
description: Draft fixed-input n8n triage workflow scaffolds and a matching local script from author-reviewed JSON-emitting snippets; inspect composition before any authorized execution.
owner: bcgov
---

# n8n Workflow Builder

## Use When

- Composing reviewed local collection snippets and report templates into a draft triage workflow.

## Don't Use When

- Cleaning raw runbooks: use the canonical n8n-runbook-parser Extension. Dynamic request-to-shell parameters and automatic API publication are outside this authoring workflow.

## Workflow

1. Inventory the reviewed snippet files, their output contracts, target namespace, group and report filenames. Record all author-approved literals; inspect commands and effects rather than trusting a read-only label.
2. Copy assets/skeleton.json as an incomplete scaffold. Replace REVIEWED_NAMESPACE, REVIEWED_SNIPPET.sh, REVIEWED_GROUP and REVIEWED_REPORT.md only with reviewed literals. Validate a Kubernetes namespace as a lowercase DNS label (letters/digits/hyphens, alphanumeric ends, at most 63 characters); keep script/group/report names to reviewed local basenames without shell syntax.
3. Keep webhook request data out of every command, namespace, script path, group and report filename. A webhook only triggers this fixed workflow. Collect might become NAMESPACE=sample-dev snippet-cache-status.sh; query text cannot change that authored command. Use the same literal in the local equivalent.
4. Give collection nodes distinct names/IDs and join their JSON outputs with merge.sh. Correct and review non-JSON producers before composition. Transfer upstream output using the scaffold base64 data channel; it is data, not a command selector.
5. Inspect report content provenance and output exposure. The scaffold responds as text/plain and does not interpret collected output as HTML. The separate local view.sh helper still renders Markdown as HTML; inspect provenance before separately authorized local use.
6. Emit JSON plus a filled assets/local-workflow.sh equivalent. Record unresolved placeholders, node/version support, script locations, input/output checks and proposed validation. Scaffolds are not import-ready or runtime-tested. Execution, authentication, publication and activation need separate authorization and target-environment verification.

## Rules

- Keep commands and paths author-reviewed literals. Defer dynamic shell input rather than treating quoting as a general parameter API.
- Read-only/idempotent are review objectives, not safety guarantees. Check snippet effects, access, concurrency and data exposure.
- The bundled scripts remain inert during package review. For later authorized use, sync.sh writes beside the selected config; inspect its destination before syncing.
- push.sh performs authenticated remote writes; pull.sh contacts the configured host and writes local workflows. Resolve the actual N8N_URL and authorization before either operation; never expose the key in reports.

## Examples

- Namespace sample-dev, snippet-cache-status.sh and a reviewed report: draft fixed commands, a no-query webhook URL and a local equivalent; deliver the review checklist without claiming a run.

## Edge Cases

- Snippet emits non-JSON: repair its output contract before adding it.
- Target n8n lacks a node/version: leave compatibility unverified and obtain target-specific guidance before import.
- Missing reviewed literals: retain conspicuous scaffold placeholders and stop before execution.

## References

- [Node composition](references/N8N_NODES.md) describes the scaffold boundaries.
- [Local mapping](references/LOCAL_WORKFLOW.md) maps nodes to shell stages.
- [API fields](references/API_SCHEMA.md) are a starting reference, not a target-version guarantee.
- [Canonical parser cleaning guidance](https://github.com/bcgov/agent-marketplace/blob/main/skills/community/n8n-runbook-parser/references/CLEANING.md) is a separate dependency; an individual install does not include it.
- assets/skeleton.json, assets/sticky-note.md and assets/local-workflow.sh are incomplete authoring templates; scripts/ contains helpers to inspect before separately authorized use.
