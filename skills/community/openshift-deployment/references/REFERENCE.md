# Workload references

Consult the current cluster version and project policy before drafting a change.

- [Kubernetes workloads](https://kubernetes.io/docs/concepts/workloads/): controller semantics.
- [Horizontal autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/): supported targets and metrics. HPA does not apply to a DaemonSet.
- [Persistent volume expansion](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#expanding-persistent-volumes-claims): StorageClass/driver prerequisites and PVC expansion behavior. Use the platform-supported process for existing claims; do not resize by editing StatefulSet claim templates.
- [Security context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/): container settings to assess against application and admission requirements.
- [Disruption budgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/): voluntary disruption behavior and availability tradeoffs.
- [BC Gov developer portal](https://developer.gov.bc.ca/): locate applicable Private Cloud platform guidance.

Review example: a stateless service with three replicas and absent probes/resources
needs application health semantics, measured requests, termination behavior and
spread/disruption choices. A proposed manifest does not prove admission or rollout.
Do not extrapolate a stateless HTTP example to database replicas or DaemonSets.
