# Team 0 environment, tenant and multi-cluster v1 audit

## Audited baseline

* Main SHA: `ee8bb0363df503e60c85136f6d46ecb6ce606633`.
* Executable terminal migration: `0026_stream_anomaly_retention_intelligence`.
* Helm chart/application: `0.2.0` / `0.2.0`; declared Kubernetes target `>=1.30.0-0 <1.31.0-0`.
* Supported matrix: no supported entries; Elasticsearch `9.4.2`, Kubernetes `1.30.x`, and the Kind topology are `unvalidated`.
* Release decision: `NO_GO`, manifest `not_published`.

## Scope audited

`helm/dataobs` packages API, Console, quality/scanner/pathway workers, monitor runtime, Kafka observer, migration Job, services, ingress, service accounts, PDBs, HPA and NetworkPolicies; it does not package Elasticsearch. Legacy `k8s/` manifests cover a smaller workload set. Backup/restore and support-bundle scripts, Kind smoke and Helm upgrade harnesses, exact-SHA release workflows, platform operations API, security route policy, tenant collection APIs and the migration registry were inspected.

Terraform roots are `aws-backend`, `aws-ec2-otel-agent`, `elasticsearch/server`, and `elasticsearch/tenant`; modules are `amg`, `amp`, `grafana-dashboards`, `iam`, and `osis`. No canonical EKS prerequisite root existed. Existing HPA covers API/Console CPU; singleton workers need lease evidence before scaling.

## Architecture classification

| Asset | Classification | Decision |
|---|---|---|
| Kubernetes + `helm/dataobs` + external Elasticsearch | `canonical` | Sole current product deployment contract |
| Shared external Elasticsearch with tenant/environment filters | `canonical` | Default logical isolation |
| `infra/terraform/aws-ec2-otel-agent` | `supported_reference` | Optional AWS telemetry prerequisite only |
| `infra/terraform/aws-backend`, AMG/AMP/OSIS modules | `legacy` | OpenSearch-centric observability experiment; not product persistence |
| `infra/terraform/elasticsearch/server` AWS OpenSearch | `deprecated` | Misnamed and incompatible with canonical Elasticsearch contract |
| `infra/terraform/elasticsearch/tenant` single-AZ per-tenant OpenSearch + CCR | `deprecated` | Conflicts with shared default, contains secret-shaped variables, and treats products ambiguously |
| older `k8s/` manifests | `legacy` | Incomplete; Helm supersedes them |
| dedicated/namespace tenant profiles | `experimental` | Unimplemented and unvalidated |

Nothing was deleted: classifications retain historical context while preventing contradictory production claims.

## Gaps and decision

Missing were durable environment/cluster/installation registries, state machines, staged offboarding, desired state, drift/skew/fleet inventory, placement, machine-readable HA/capacity, DR metadata, lifecycle APIs and hosted certification. HA lacks retained failure-domain evidence; DR lacks cross-region recovery evidence; two-cluster certification is pending.

Migration decision: generic resources cannot express independent strict current-state/OCC and append-only lifecycle evidence, so add forward-only `0027_platform_environment_tenant_multicluster_lifecycle`; historical migrations remain unchanged. Backup scope must include its current-state indices and evidence stream before production activation.

Cross-team dependencies: Team 5 consumes UI contracts only; IAM/privileged approvals and release orchestration remain Team 0 foundations; product teams must preserve tenant/environment filters and worker lease semantics. Elasticsearch, OIDC, Kubernetes, ingress/DNS, OTLP and snapshot providers remain external operator dependencies.
