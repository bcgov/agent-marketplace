# Create an extension

Use the installed `bcgov-create-extension` companion with this request:

> Create a small community skill that turns a public meeting agenda into an
> action checklist. Preview the public files, capabilities, and warnings, but
> do not submit anything.

The companion should ask for missing type or specialty information, scaffold a
package, run local validation, show the public diff, and stop before branch,
commit, push, or pull-request actions. For a checkout-level demonstration,
the equivalent maintainer command is:

```bash
uv run python scripts/create_extension.py init \
  --marketplace . \
  --name meeting-action-checklist \
  --display-name "Meeting Action Checklist" \
  --description "Turn public meeting agendas into action checklists." \
  --summary "Creates a concise action checklist from a public meeting agenda." \
  --maintainer @bcgov/platform-services
uv run python scripts/create_extension.py preview \
  --marketplace . \
  --name meeting-action-checklist
```

Run this only in an isolated checkout or remove the unsubmitted package
afterward. Do not run `submit` during onboarding.
