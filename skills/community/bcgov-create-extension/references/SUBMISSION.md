# Marketplace package and contribution

Use this reference for a marketplace submission. Local drafting can finish without
any public write. Only explicitly selected public input belongs in the package.

1. Select skill, instructions, prompt or agent and a registered Specialty (or
   Community). Use `<type-directory>/<specialty>/<name>/`; skill native content
   is SKILL.md, other native files are `<name>.<type>.md`.
2. Add bcgov-extension.yaml with real maintainers and truthful capabilities.
   Native description can supply summary; use an explicit summary if absent.
   Read current [asset spec](https://github.com/bcgov/agent-marketplace/blob/main/spec/ASSET_SPEC.md)
   and schema. Preserve existing canonical identity during a Specialty transfer.
3. Inspect every public file, native metadata, links, resource paths and declared
   access. Treat bundled scripts as data. Manual content exercises and automated
   package checks are separate from actual client/model evidence.
4. Show the reviewable public files/diff, inventory, capabilities and unresolved
   findings. Existing task authority can authorize submission; otherwise obtain
   it before public writes. Use an available GitHub integration, or the
   [browser contribution page](https://bcgov.github.io/agent-marketplace/contribute.html).
   Its native-file prefill is file 1, not a two-file upload: commit the Manifest
   to the same fork and branch, then inspect both paths in one PR.
5. Use the one type-neutral PR template. Fix CI findings on the same branch.
   Generated Catalogue/site outputs are CI builds; edit authored inputs, not
   generated projections. An unconfirmed public membership routes to human
   review; format/security failures still need fixes. Specialty content requires
   owning-team review when ready. A passing route is not proof an automatic
   merge or deployment occurred; activation controls can remain off.
6. Report the PR URL and exact-head check state, or preserve the draft and give
   the access/signing/retry step. Validate actual native placement with the
   selected Catalogue install-options; no unsupported client install action.

Published source evidence comes from
https://bcgov.github.io/agent-marketplace/assets/catalog.json. A supplied preview
may be useful before publication, but its full source revision must be labeled.
No v1 deployment is asserted merely by following this guide.
