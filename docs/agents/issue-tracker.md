# Issue tracker: GitHub

Issues and specs for this repo live in GitHub Issues for `bcgov/agent-marketplace`. Always pass `--repo bcgov/agent-marketplace` to `gh` commands: this checkout's plain `gh` default resolves to the upstream `bcgov/agent-skills` repo.

## Conventions

- **Create an issue**: `gh issue create --repo bcgov/agent-marketplace --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --repo bcgov/agent-marketplace --json number,title,body,labels,comments`.
- **List issues**: `gh issue list --repo bcgov/agent-marketplace --state open --json number,title,body,labels,comments` with appropriate `--label` and `--state` filters.
- **Make an issue a sub-issue of a parent**: `gh issue create --repo bcgov/agent-marketplace --parent <parent> ...`, or `gh issue edit <parent> --repo bcgov/agent-marketplace --add-sub-issue <child>` (requires `gh` 2.94+). Without sub-issues, put `Part of #<parent>` at the top of the child body.
- **Blocking**: Use GitHub's native issue dependencies. Add an edge with `gh issue create --repo bcgov/agent-marketplace --blocked-by <n>,<n> ...` or `gh issue edit <child> --repo bcgov/agent-marketplace --add-blocked-by <blocker>` (requires `gh` 2.94+). Where unavailable, put `Blocked by: #<n>, #<n>` at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Count open blockers**: `gh api --repo bcgov/agent-marketplace repos/bcgov/agent-marketplace/issues/<n> --jq .issue_dependencies_summary.blocked_by`. `gh issue view <n> --repo bcgov/agent-marketplace --json blockedBy` also lists closed blockers; filter to open ones.
- **Comment / label / close**: Use `gh issue comment`, `gh issue edit --add-label` / `--remove-label`, and `gh issue close`, always with `--repo bcgov/agent-marketplace`.
- File issues only in `bcgov/agent-marketplace`, never in `mattpocock/skills` or the upstream `bcgov/agent-skills` repository.

## Pull requests as a triage surface

**PRs as a request surface: no.** Set this to `yes` only if this repo decides to triage external PRs like issues.

When enabled, PRs use the same labels and states as issues, with the `gh pr` equivalents. Always pass `--repo bcgov/agent-marketplace`.

## When a skill says “publish to the issue tracker”

Create a GitHub issue in `bcgov/agent-marketplace`.

## When a skill says “fetch the relevant ticket”

Read the issue with `gh issue view <number> --repo bcgov/agent-marketplace`.
