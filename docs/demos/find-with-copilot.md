# Find an extension with Copilot

From a workspace containing the installed `bcgov-find-extension` companion,
ask:

> Find an extension that helps me review repository security hardening. Show
> the best match, its capabilities, owner, source revision, digest, and review
> status, then wait for confirmation before showing installation steps.

The expected match is the active security package
`bcgov-public/repo-hardening`. Compare its evidence with the same record on
the generated catalog page. The companion should return no more than three
deterministically ranked results and should not describe marketplace listing as
a blanket safety guarantee.

Reset by ending the Copilot conversation; no repository files need to change.
