# Subnet design reference

Use these primary sources for the specific deployment being reviewed; record the
service/API version and consulted policy revision in the plan.

- [BC Gov Azure networking](https://github.com/bcgov/public-cloud-techdocs/blob/main/docs/azure/design-build-deploy/networking.md): current platform boundaries and change requests.
- [Bicep resource dependencies](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/resource-dependencies): independent resources can deploy in parallel; a common parent does not order sibling resources.
- [Private endpoint network policies](https://learn.microsoft.com/en-us/azure/private-link/disable-private-endpoint-network-policy): select the policy behavior required by the current design.

For two conflicting subnet writes, draw the dependency first -> second explicitly
in the selected IaC tool, then inspect the resulting plan. A shared VNet reference
alone is not evidence that one sibling waits for the other. Avoid blanket claims
about service delegations, address consumption or provider locking across versions.

The deliverable is a proposed CIDR/delegation/NSG configuration, assumptions,
platform approvals needed, and a validation plan. Execution results remain unknown
until the authorized command actually runs.
