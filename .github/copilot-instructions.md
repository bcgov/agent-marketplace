# Agent navigation

When using GitHub CLI in this checkout, specify `--repo bcgov/agent-marketplace` for issue and pull-request operations. `gh repo view` can otherwise resolve the `upstream` remote (`bcgov/agent-skills`) instead of this repository.

Run the repository's existing checks through `make verify`; consult `Makefile` and `.github/workflows/pr.yml` for their current scope.
