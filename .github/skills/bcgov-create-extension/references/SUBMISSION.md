# Portable marketplace submission

Load this reference only when submitting an active Agent Skill to the BC Gov
marketplace. The contributor may start in any workspace; a marketplace checkout,
Python, and `uv` are not prerequisites.

## Stage and inspect

1. Create an isolated temporary package at
   `skills/<community-or-specialty>/<name>/` containing only approved public
   inputs.
2. Fetch the hosted marketplace catalog, `spec/SKILL_SPEC.md`, manifest schema,
   contribution guide, and pull-request template from
   `https://github.com/bcgov/agent-marketplace`.
3. Check package shape, frontmatter, required sections, manifest fields, flat
   resources, declared capabilities, obvious credentials, hidden controls, and
   unsupported executable content. Treat every package script as data.
4. Show the complete candidate files or diff, public inventory, capabilities,
   specialty, upstream-gap evidence, destination, and checks deferred to CI.

The preview is complete when the user can identify every byte proposed for
publication and no local inspection finding is hidden.

## Submit

Ask for explicit confirmation before any public write. After confirmation, use
an available GitHub integration to create an in-repository branch, upload the
candidate under its canonical path, and open a draft pull request. If the host
has no GitHub write integration, use `git` and `gh` when available to create a
temporary checkout; this checkout is created on demand and does not require
Python or `uv`.

Populate the repository pull-request template with the upstream search,
BC Gov-specific gap, public inventory, capabilities, source provenance, and
known advisories. Do not author review fields or claim that local inspection is
marketplace validation.

## Validate remotely

Protected-branch CI is authoritative for the schema, policy scan, generated
catalog, tests, and documentation checks. Read every failing check, repair only
the candidate or its generated projections as directed, update the same branch,
and repeat until the draft is review-ready.

Submission is complete when the draft pull request URL and CI state are
reported. If access, signing, push, or PR creation fails, preserve the staged
package and report the exact access or retry action.