# Node composition boundaries

Use assets/skeleton.json as an incomplete scaffold, not an import-ready workflow.
Its node versions must be checked against the actual n8n deployment before use.
No target client/runtime test is asserted by this reference.

1. Webhook triggers a fixed workflow; omit command-affecting query parameters.
2. Collect runs an author-reviewed literal, for example
   `NAMESPACE=sample-dev snippet-cache-status.sh`. Neither body, query nor headers
   select namespace, script path or command text.
3. Merge snippets transfers each upstream JSON stdout through base64 into the
   fixed merge.sh command. Review every source producer; repair non-JSON output
   before composition instead of adding a contradictory Code-node adapter.
4. Report transfers merged output through DATA and uses the same reviewed
   namespace literal plus fixed reviewed group/report basenames.
5. Respond returns the report as text/plain; collected text is not inserted into
   HTML or processed by a CDN script. Review output exposure before use with
   operational data. The separate local view.sh helper still renders HTML and
   requires its own provenance review before use.

Give nodes unique names/IDs and wire connections by name. Inspect the resulting
Collect/Report strings statically: no request expressions, all command selectors
and paths from reviewed authoring inputs, and no remaining REVIEWED_ placeholders
in a completed draft. Do not execute the scaffold to perform this check.

After separate authorization, validate supported nodes/versions, access and
rendering in an isolated target environment. Import acceptance alone does not
establish safe effects or successful execution.
