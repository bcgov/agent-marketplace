# Temporary CI probe — safe to delete

This file exists only to trigger the **Community intake** workflow once, so its
`intake` status check becomes selectable in the `main` branch ruleset
(Settings → Rules → Rulesets → Require status checks → Add checks).

It is not a skill package (there is no `bcgov-extension.yaml`), so it produces no
catalog entry and changes nothing a user can install.

**After `intake` appears in the required-checks picker and you add it, close this
PR and delete the `ci/register-intake-check` branch.**
