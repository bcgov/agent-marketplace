---
name: openshift-deployment
description: Review or draft workload manifests inside an existing OpenShift namespace, including controller choice, resources, probes, security context and scaling tradeoffs.
owner: bcgov
---

# OpenShift Workload Review

## Use When

- Reviewing a Deployment, StatefulSet, DaemonSet, Job or CronJob in an existing project.

## Don't Use When

- Cluster administration, namespace provisioning or changing platform policies; seek the platform-supported process.

## Workflow

1. Collect workload semantics, controller, availability objective, namespace constraints and supplied measurements. Record missing evidence.
2. Choose the controller appropriate to state and scheduling needs. Review resources from measurements and quota; propose requests and limits with reasons rather than universal ratios.
3. Check readiness, liveness and startup behavior against the application. Review termination and disruption tolerance; select spread and disruption settings consistent with the availability objective.
4. Review least-privilege security context against the namespace admission policy and image behavior. Identify writable paths needed by a read-only root filesystem and avoid prescribing fixed UIDs without platform evidence.
5. Consider HPA only for a supported scale target and workload that can scale horizontally with available metrics. DaemonSets are not HPA targets. Explain stateful or singleton constraints instead of mandating autoscaling.
6. Deliver a manifest diff, assumptions and validation plan. Distinguish local analysis from authorized server admission checks and observed rollout behavior.

## Rules

- Cite current project/platform policy for admission limits; this skill is not a substitute for those policies.
- Storage expansion depends on the StorageClass, driver and platform procedure. Editing StatefulSet claim templates and restarting Pods is not a supported general resize recipe.
- Preserve existing data and service continuity; propose destructive operations only with a reviewed migration plan and authorization.

## Examples

- Three-replica stateless Deployment with no probes or requests: propose measured resource requests, application-specific health probes, termination handling and disruption/spread review; HPA needs metrics and a scaling rationale.

## Edge Cases

- PVC needs growth: identify the existing claim, StorageClass expansion support and platform-supported procedure before proposing a PVC request change.
- No cluster access: report admission/runtime results as unverified and finish the manifest review.

## References

Use [workload references](references/REFERENCE.md) for controller, scaling, storage and platform sources.
