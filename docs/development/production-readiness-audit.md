# Production readiness audit

This PR establishes product foundations and does not make DataObs production-ready.

| Capability | Current state | Target | Evidence | Blocker | Milestone |
|---|---|---|---|---|---|
| API | FastAPI/Uvicorn with legacy routes and `/api/v1` foundations | Hardened public API | `src/api/app.py` | IAM/rate limits incomplete | v1 |
| auth | Local shared bearer token and pluggable principal abstraction | OIDC/API keys/RBAC | `src/api/app.py` | Full IAM non-goal | v1.x |
| tenancy | Header tenant context and tenant-aware contracts | End-to-end tenant isolation | domain models/API tests | deeper auth scopes | v1 |
| Elasticsearch migrations | Explicit migration CLI and readiness status | Versioned upgrade framework | `packages/elastic_store` | real cluster validation | v1 |
| collection manager | Minimal source/scanner/task/result control plane | Fleet/EDOT orchestration | `services/collection_manager` | adapters stubbed | v1.x |
| scanner | Synthetic result ingestion only | real connector vertical slices | scanner worker + collection manager | PostgreSQL scanner non-goal | follow-up |
| connectors | References and SDK boundaries | certified connectors | docs/integrations | connector implementation | follow-up |
| CI | Unit checks extended | blocking integration gates | `.github/workflows/ci.yml` | external services | v1 |
| Docker | Existing API/quality images | product images with SBOM | Dockerfiles | collection-manager image hardening | v1.x |
| Helm | Existing chart validation | production chart | `helm/dataobs` | secrets/HA | v1.x |
| Terraform | Existing modules | deployment blueprints | `infra/terraform` | production environments | v1.x |
| security | Secret-reference serialization | threat model and scanning | domain/source model | full security review | v1 |
| observability | audit events and OTel hooks | self-observability dashboards | collection manager telemetry | dashboards | v1.x |
| backup/restore | documented as blocker | tested snapshots | operations docs | automation non-goal | later |
| upgrades | migrations record state | safe blue/green upgrades | elastic_store | rollback automation | later |
| licensing | OSS repo license retained | dependency/license policy | LICENSE | legal review | v1 |
| UI | Kibana primary, future console | DataObs Console | README | React console non-goal | later |
| Streams | data stream templates only | Kafka/Elastic Streams packs | manifest | implementation non-goal | later |
| Workflows | execution contracts only | remediation packs | domain/workflow | production packs non-goal | later |

## Incident automation audit note

Incident automation remains a draft vertical slice until container-backed CI proves Elasticsearch/Kibana 9.4.2 migrations, workflow deployment, alert-rule bindings, Cases integration, safe approvals, notification fallback, E2E recovery and sentinel-secret scans.
# Kafka DSM completion-gate status

The Kafka Observer and Pathway Worker now have executable long-running and
single-cycle command paths. Their production repositories write inventory,
current projections, topology edges, immutable observations, and checkpoints to
Elasticsearch. Plaintext Kafka is rejected outside development/test, secrets are
resolved only from environment or file references, and span normalization never
captures message bodies.

This is a completion gate, **not a production-readiness claim**. In particular,
the container-backed three-broker/Kibana workflow demonstration, Kafka Connect
and Schema Registry profiles, Cases execution, lease-based multi-worker
coordination, and end-to-end failure/recovery evidence remain blocking work. The
standalone console and any destructive or autonomous remediation remain out of
scope.
