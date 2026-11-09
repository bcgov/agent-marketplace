---
name: azure-networking
description: Design or review subnet, NSG and private-endpoint changes inside an existing Azure VNet; diagnose subnet deployment conflicts and produce a reviewable plan.
owner: bcgov
---

# Azure Networking

## Use When

- Adding a subnet or reviewing delegation, address space and NSG requirements in an existing VNet.

## Don't Use When

- VNet provisioning, topology redesign or platform-protected network changes: obtain platform guidance first.

## Workflow

1. Collect the existing VNet ID and address spaces, current subnet CIDRs, target service, IaC tool/version and supplied platform rules. Mark unavailable inputs.
2. Consult the platform networking reference before proposing changes. Keep VNet address space, DNS, peering and route-table changes outside the draft unless the platform owner explicitly authorizes them.
3. Propose a non-overlapping CIDR, service-specific delegation and NSG attachment in the subnet definition. Verify current service requirements rather than copying a generic NSG table.
4. Inspect dependencies between sibling writes. Bicep resources without dependencies can deploy in parallel; sharing a parent does not order siblings. For a demonstrated write conflict, propose explicit dependencies or sequential operations.
5. Deliver the proposed subnet properties, assumptions, downstream subnet ID output and validation plan. Run live validation or apply only within the user-authorized scope; report the actual result separately from the plan.

## Rules

- Preserve existing platform-managed resources and supplied policies. Confirm current constraints rather than treating this skill as platform policy.
- Check private-endpoint network policy and delegation requirements for the selected service/API version.
- A successful build or what-if is partial evidence; it does not establish runtime reachability or guarantee a subsequent apply.

## Examples

- Existing VNet, two proposed sibling subnets, intermittent AnotherOperationInProgress: inspect the deployment graph and propose an explicit dependency between the conflicting subnet writes. Do not claim Bicep serializes the scope automatically.

## Edge Cases

- Missing address-space inventory: produce the required-input list instead of guessing an available CIDR.
- A delegation change affects an existing service: document impact and obtain its supported migration procedure before proposing destructive replacement.

## References

Read [the focused reference](references/REFERENCE.md) for dependency and platform source links.
