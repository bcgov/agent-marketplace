# Hosted Extension quality decisions

Review date: 2026-11-03. This records content decisions, not runtime certification.
All nine existing canonical identities and legacy aliases remain active; no
retirement, replacement or snapshot rewrite is proposed. Existing maintainer
entries are preserved. New Community examples are maintained by @Krocodial.

| Existing skill | Outcome | Bounded correction and manual content exercise |
| --- | --- | --- |
| azure-networking | Rework | Existing VNet + two sibling subnet writes -> explicit input inventory and dependency review. Removed the false guarantee that Bicep serializes a scope, generic service rules and unsupported destructive recovery recipes. Output is a proposed CIDR/delegation/NSG plan; apply/reachability remain unverified. |
| bcgov-create-extension | Rework | Pasted runbook rules + local-draft request -> one native instructions file and minimal Manifest; local drafting can finish before submission. Uses the published Pages Catalogue, BC Gov-only lookup, two-file same-branch browser journey, current lifecycle and tested install-options. Static trigger inspection is separated from client evidence. |
| bcgov-find-extension | Rework | Release-note prompt request without installation -> BC Gov four-type lookup and an honest no-match result if needed. Removed External search/registration promises; shared native choice and lifecycle guidance retained. This content correction does not claim the separate finder helper migration has completed. |
| github-actions | Rework | External fork requests lint/tests -> unprivileged pull_request validation, with a separate trusted boundary for privileged effects. Removed fail-every-fork guidance, only-one-required-check rule and false immutable-major-tag guarantee. |
| github-repo-setup | Rework | Documentation-only repo + unavailable API -> N/A application controls, Unverified server controls, score only inspected dimensions and report coverage. Replaced unsupported compliance/vendor claims and secret-strength inspection with a scoped evidence rubric; weighted denominator is explicit. |
| n8n-runbook-parser | Rework | Local runbook with a fenced status command -> extraction/cleaning inventory and drift/backport plan. Corrected missing-helper references to existing doc_links.py plus doc-url-shim-template.sh; clarified doc-less placeholders and mixed status ownership. Extraction/sealing are not claimed executed here. |
| n8n-workflow-builder | Rework | Reviewed namespace sample-dev + snippet-cache-status.sh -> fixed literal collection command, same literal in Report/local equivalent, no request-derived command selectors. Scaffold is conspicuously incomplete, not import-ready; non-JSON producers need correction before composition. Respond returns text/plain instead of interpreting collected HTML. |
| openshift-deployment | Rework | Three-replica stateless Deployment without probes/requests -> measured resource and application health review, disruption/spread decisions and conditional HPA assessment. Removed blanket HPA/vertical-scaling rules and unsupported PVC/template restart recipe; live admission and rollout remain unverified. |
| security/repo-hardening | Keep | Supplied missing reviews/unknown scanning/workflow write permission -> scoped gap list, evidence gaps and proposed corrections. Existing bounded checklist retained byte-for-byte. Any future Specialty content edit requires owning-team review; no Security approval is claimed here. |

Parser and builder can contact user-configured remote hosts, including redirects.
Their network wildcard discloses that existing access rather than inventing a
fixed allowlist; it raises declared risk and remains a human-review concern, not
runtime confinement. Environment declarations enumerate referenced variables,
including shell-local/template names recognized by the deterministic scanner.
No bundled package code was executed for this review. The builder's separate
local HTML view helper still needs provenance review before authorized use.

Primary technical references checked for the corrections: [Bicep dependencies](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/resource-dependencies),
[GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use),
[Kubernetes autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
and [volume expansion](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#expanding-persistent-volumes-claims).
The revised infrastructure skills direct version/platform-specific decisions to
current primary documentation; they do not invent universal platform policy.

## Three useful Community examples

These two-file packages also illustrate realistic browser contribution inputs.
The native file supplies its summary through description; the Manifest contains
only maintainers and capabilities. Prompt/agent tools are empty, with no model
or agent override. These capability declarations describe behavior after
installation; installer writes are governed by the selected placement action.

### runbook-review-evidence (instructions)

Task: improve supplied docs/runbooks/cache-check.md reading "Check cache health
using the existing project dashboard. If unhealthy, call support", without
executing it.

Manual content result: prerequisites list dashboard access and the missing URL;
action says open [dashboard URL required] and select the project cache;
expected observation is health status and timestamp; recovery records status/time
and contacts [support channel required]. Validation is "Not executed; owner must
supply dashboard and support values". No contact or successful result is invented.

The guidance applies to docs/runbooks/**/*.md, with read/write access limited
to those documents. Placement maps to
.github/instructions/runbook-review-evidence.instructions.md. Glob matching and
instruction application by a live client were not tested; explicit attachment
and client discovery need separate observation.

### change-summary (prompt)

Task: summarize supplied export change for reviewers: zero-balance rows are now
included; fixture has two positive rows and one zero row, expected count three;
no execution result supplied.

Manual content result: Change: include zero-balance rows. User impact: exports
include records previously omitted. Validation: expected three records from the
supplied fixture; execution result not provided. Open questions: confirm fixture
execution and negative-balance behavior. No passing test or deployment is asserted.

The prompt uses only conversation material and declares capabilities: none.
Placement maps to .github/prompts/change-summary.prompt.md.

### acceptance-reviewer (agent)

Task: review criteria (1) canonical filename, (2) matching installed bytes,
(3) live client discovery. Supplied evidence contains the canonical path and
matching source/destination SHA-256 values, but no client transcript.

Manual content result: criterion 1 Supported by the supplied path; criterion 2
Supported by the supplied comparison, not independently reproduced by the agent;
criterion 3 Missing evidence, next check select/invoke the agent in the intended
client and record the result. The role stops after the evidence review.

The agent declares capabilities: none and no tools. Placement maps to
.github/agents/acceptance-reviewer.agent.md; this format is not advertised as
Codex TOML or another client's configuration.

## Verification boundary

Each new package passes the public submission analyzer without blocking findings
and has a VS Code Local manual project install choice. Actual isolated native
file copying, SHA-256 comparison, collision refusal, removal and reinstallation
are recorded for all three examples. The governance Manifest is not copied.
See [the native install evidence](INSTALL_TEST_MATRIX.md) for the layout contract.
The supported Linux make verify gate validates all packages and generated output.

The examples above are manual content exercises, not model/client execution.
No client discovery, prompt invocation, agent selection, operational runbook,
n8n workflow or infrastructure change was executed. No publication, merge-route
activation or deployment is claimed; controls remain off. Real non-writer
browser/fork and Specialty-review journeys remain separate contribution evidence.
