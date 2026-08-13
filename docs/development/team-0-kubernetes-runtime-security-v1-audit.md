# Team 0 Kubernetes runtime security v1 audit

## Immutable baseline

* Audited clean `main` commit: `141ec42b82f236b7a2858c85351e174a511c9f3f` (the repository has no configured remote, so this is the latest locally available clean main-equivalent commit).
* Executable registry terminal migration: `0030_team1_multi_broker_messaging_runtime`, derived with `python scripts/release/current_terminal_migration.py`. Production values incorrectly named `0029_team2_data_intelligence_reconciliation`; this change corrects the reference without changing a released migration.
* Chart/application: `0.2.0` / `0.2.0`; chart target: Kubernetes `>=1.30.0-0 <1.31.0-0`.
* Canonical production path: `helm/dataobs` with `values-production.yaml`. `k8s/*.yaml` is **legacy/development reference**, is not production-supported, and must not be used to assert security compliance. `deploy/kubernetes/namespace-production.example.yaml` is **supported-reference**. Rendered and evidence files are **generated**. `deploy/policy/kyverno` is **experimental/optional reference**.

## Inventory

The Helm workloads are Deployments for API, Console, quality worker, scanner worker, monitor runtime, pathway worker, Kafka observer, and optional bundled OTEL Collector, plus a migration Job. Templates also define component ServiceAccounts, ClusterIP Services, API/Console Ingresses, HPAs, PDBs, ConfigMaps, and NetworkPolicies. There are no StatefulSets or CronJobs. Raw `k8s/` contains namespace/configuration, API/monitor/quality Deployments, OTEL, and API Service manifests; these duplicate only a subset and are weaker legacy examples.

Canonical pods set `runAsNonRoot`, `RuntimeDefault` seccomp, `allowPrivilegeEscalation: false`, read-only roots, and drop `ALL`; no privileged mode, added capabilities, `Unmasked` proc mount, host network/PID/IPC, host port, or hostPath was found. ServiceAccounts and pods disable token automount. No Role, ClusterRole, RoleBinding, or ClusterRoleBinding is shipped because no workload needs the Kubernetes API. Volumes/mounts are limited to ConfigMap/Secret-backed configuration and temporary `emptyDir` where used. Only the migration Job has an init-style finite lifecycle; no init containers were found.

Production defines CPU/memory requests and limits for enabled containers, API and Console TLS Ingress, ClusterIP Services, API/Console PDBs, and topology spread across `topology.kubernetes.io/zone`; this configures scheduling but is not multi-AZ evidence. HPAs are optional. API has startup, readiness, and liveness probes; workers use their process/lease health model rather than meaningless HTTP probes.

NetworkPolicy is enabled with component ingress, DNS, and required dependency egress. Native NetworkPolicy cannot prove FQDN identity for Elasticsearch/OIDC/OTLP; production needs a capable CNI, egress gateway, firewall, or cloud control. Broad customer CIDRs are reported and require review.

External Elasticsearch and OIDC are assumed; neither is embedded. Credentials, CA material, API signing/encryption keys, and telemetry authentication use Secret references. ConfigMaps contain non-secret configuration. Production Ingresses have TLS secret references; ingress-class-specific annotation safety remains the operator's responsibility.

Images use `ghcr.io` plus repositories, `IfNotPresent`, readable `0.2.0` tags, and digests. Existing repeated-character digests are placeholders, not artifacts, so production render/certification intentionally fails until real release digests are supplied. Registry patterns are customer-configurable validator inputs and credentials are never emitted.

Existing controls include release metadata and terminal-migration scripts, migration immutability, SBOM/signature/provenance certification workflows, redaction and artifact verification. This work consumes those identities rather than introducing signing. No hosted cluster or CNI enforcement evidence was available during audit.
