---
name: n8n-runbook-parser
description: Extract local or explicitly approved remote runbook sources into snippets, inspect doc/code drift and propose reviewed backports; author RunbookParser configuration and cleaning plans.
owner: bcgov
---

# n8n Runbook Parser

## Use When

- Extracting runbook code, comparing source drift or preparing reviewed cleaned snippets.

## Don't Use When

- Publishing n8n workflows: use the separate n8n-workflow-builder Extension. Plain document editing without extraction needs no parser.

## Workflow

1. Locate the installed package and selected workspace config. Review root, destination and working_dir before any writes. Use Python 3.12+ with PyYAML and markdown-it-py already available; dependency installation is a separate action.
2. For each real source, set exactly one file or url and a useful description. A deliberately doc-less source may omit both for hand-authored include; it contributes no extracted content. Prefer a local file for an offline task.
3. Review scripts/parser.py as data before separately authorized execution. Use its explicit --config path and ingest --dry-run first; inspect planned outputs before ingest. check and diff report drift; they do not certify snippet safety. Consult CLI usage for actual command order and exit codes.
4. For cleaning, inspect raw code and prose, select bounded collection behavior and document side effects and parameters. Write cleaned snippets and skipped reasons; run an appropriate authorized linter only when requested. Use include/seal for the recorded baseline after reconciliation.
5. Preserve parser-owned sources and seal state. The author may maintain cleaned/skipped and docs topics as documented in CONFIG; these are not all machine-owned fields.
6. For doc links, the existing scripts/doc_links.py validates/prunes URLs AND generates url-shim-<group>.sh from assets/doc-url-shim-template.sh. Use --config and --dry-run before an authorized network/write operation. Review registry values as code-generating input before using the generated shell.
7. Deliver extracted/cleaned inventory, drift findings, skipped reasons and proposed backports. Report actual execution evidence separately from manual content inspection.

## Rules

- Read-only and idempotent are cleaning objectives requiring review, not guarantees from a label or parser seal.
- Keep generated raw content canonical to the source. Edit the source and re-ingest instead of silently changing raw extraction.
- Remote source/doc-link requests follow redirects and can contact configured hosts beyond GitHub. Inspect destinations and obtain access authority; the broad network capability is disclosure, not confinement.
- Render/report helpers belong to the separately installed builder; no tools/n8n helper is bundled by this package.

## Examples

- Local runbooks/cache.md with a fenced status command: plan a file source, raw extraction inventory and a cleaned collection draft; mark parser execution and target behavior unverified until separately observed.

## Edge Cases

- No source document: use a deliberate placeholder with include and record that no backport target exists.
- Remote fetch falls back to cache: identify cached evidence rather than claiming a fresh source observation.

## References

- [Configuration](references/CONFIG.md), [CLI usage](references/PARSER_USAGE.md), [cleaning](references/CLEANING.md) and [backports](references/BACKPORT.md) are branch-specific references.
- assets/config.template.yaml and snippet/report/validator templates are drafts to inspect.
- scripts/doc_links.py and assets/doc-url-shim-template.sh are the existing doc-link generation path.
- [Canonical builder](https://github.com/bcgov/agent-marketplace/tree/main/skills/community/n8n-workflow-builder) owns render.sh and utils.sh; individual installation does not include it.
