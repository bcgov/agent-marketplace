# Assessment rubric

Agree applicability before scoring. These prompts are a local assessment aid;
project-specific thresholds, SLAs and mandatory controls need a cited policy.

| Dimension | Inspect |
| --- | --- |
| Repository settings | merge choices, branch cleanup and visibility |
| Review and protection | effective rulesets, review requirements, independent hard checks, force-push/deletion controls |
| Code hygiene | applicable compiler/linter configuration and measured tests |
| Secret management | documented separation, access and rotation; never secret values |
| Dependency maintenance | declared update process and observed runs; inherited policy stays Unverified until inspected |
| Vulnerability response | documented ownership, triage, project SLAs and evidence |
| CI and delivery | artifact provenance, environment approvals and observed health checks |
| Quality enforcement | actual required status checks and failure behavior |
| Workload configuration | applicable controller, probes, resources and security context |

Met = 1, Partial = 0.5, Not Met = 0. Unverified and N/A are excluded from the
score. Use a default weight of 1; if different weights are agreed, show them.

`score = 100 * sum(weight * value) / sum(weights of verified applicable dimensions)`

`coverage = verified applicable dimensions / all applicable dimensions`

Example: weights 2 and 1, Met and Partial, plus one Unverified applicable
dimension: score = 100 * (2 + 0.5) / 3 = 83.3%; coverage = 2/3.
No verified applicable dimensions means no score, not zero or full readiness.
A score is not a compliance conclusion. Record the assessment date and source
revision and give each finding its evidence, scope and next verification step.

For remediation, use the canonical marketplace records for github-actions,
openshift-deployment or security/repo-hardening. An individual skill installation
does not include sibling packages.
