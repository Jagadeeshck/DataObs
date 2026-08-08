# Multi-cluster platform v1

The registry is an inventory and deterministic planning layer, not a remote-shell or cloud manager. Cluster records contain safe metadata only; installations bind a cluster, namespace, constrained Helm release name, exact SHA, immutable digests, terminal migration and external dependency fingerprints. Kubeconfig and bearer tokens are prohibited.

Fleet health preserves `healthy`, `degraded`, `unhealthy`, `unknown`, `unsupported`, and `unvalidated`. Missing evidence is unknown. Release and terminal-migration tuples produce skew evidence; an unknown production digest or migration mismatch is security-critical. Cross-cluster operations remain operator-executed through reviewed deployment adapters.

Placement filters supported, non-maintenance installations by platform environment, region/residency, shared isolation profile and capacity preset, then sorts stable installation IDs. Results must retain eligible and excluded candidates, bounded reason codes, capacity evidence and policy version. No ML or tenant cardinality metric participates.

DR metadata records primary/recovery regions, backup repository profile, targets and rehearsal evidence. V1 produces a manual failover plan and never changes DNS or implements Elasticsearch cross-region replication. Local namespace simulations are labelled `functional_simulation`, never multi-cluster or cross-region proof.
