# Team 0 production scale and HA v1 audit

## Scope and decision

Audit base is clean `main` at `70f77d85b17776fe2222d591788f145269479057`. The terminal migration is `0027_platform_environment_tenant_multicluster_lifecycle`; this work adds no migration and retains measurements as artifacts. The current Beta 1 RC1 release decision is **NO_GO**. This audit does not cover disaster recovery, restore, RPO/RTO, cross-region recovery, or complete dependency outages.

## Packaged deployment state

The supported-platform matrix is `docs/release/supported-platform-matrix.yaml`. Existing HA profiles (`development`, `standard-ha`, `production-ha`) and capacity presets (`small`, `medium`, `large`) are explicitly unvalidated. Chart defaults/production values package API, Console, quality worker, scanner worker, monitor runtime, pathway worker, Kafka observer, and OTel Collector. API and Console production presets use 2 replicas; all workers use 1. The legacy raw manifests disagree (API 2, quality 1, monitor runtime 2) and are not certification evidence.

The chart provides optional API/Console HPA, API/Console PDB, readiness/startup probes, rolling termination, resource requests/limits, and configurable topology spread/affinity. Production topology spread is configured for API, Console and OTel, but worker constraints are empty; anti-affinity remains empty. Rendered resources are configuration evidence only—not scale, scheduling, or failover proof.

## Runtime classification

No packaged runtime has retained horizontal-scale certification evidence. Worker HPA remains prohibited.

| Runtime | Audit classification | Worker policy / reason |
|---|---|---|
| API | `horizontal_scale_candidate` | Stateless shape and chart replicas/HPA exist; runtime load/failure evidence pending. |
| Console | `horizontal_scale_candidate` | Multiple replicas packaged; browser continuity evidence pending. |
| OTel Collector | `horizontal_scale_candidate` | Two replicas preset; exporter queue/duplicate behavior pending. |
| quality worker | `singleton_unvalidated` | One replica; no retained claim/fencing/crash matrix. |
| scanner worker | `singleton_unvalidated` | One replica; no retained takeover evidence. |
| monitor runtime | `singleton_unvalidated` | Repository leases/checkpoints exist, but fencing and multi-replica evidence are incomplete. |
| pathway worker | `singleton_unvalidated` | Lease-oriented code is not certification evidence. |
| Kafka observer | `singleton_unvalidated` | One replica; partition/rebalance and checkpoint evidence pending. |

`singleton_safe`, `horizontal_scale_prohibited`, and `horizontal_scale_certified` are valid audit states but no packaged runtime currently earns them. Job reliability, incident reconciliation, stream intelligence and Collection Manager exist in source but are not separate workloads in this chart, so they are unsupported for independent replica certification rather than silently treated as packaged workers.

## Persistence, Elasticsearch, load and resilience

Elasticsearch repositories use product aliases/index constants and optimistic-concurrency/lease mechanisms in selected capabilities. Client construction is distributed across services; there is no retained whole-runtime proof for bounded query budgets, dependency latency, storage growth, retention deletion, or safe aggregate cluster telemetry. Credentials/hosts must never enter evidence.

There was no reusable `tests/performance` certification harness on the audited SHA. Existing tests include unit/integration/certification suites and Team 0 infrastructure/Kind workflows, but no retained exact-SHA staged load, noisy-neighbour, autoscaling, worker crash, pod/node failure, or 30-minute soak result. Kind can prove only `functional_simulation`; cloud multi-zone HA remains unvalidated.

Current platform SLO definitions live in `docs/operations/platform-slos.yaml` and `docs/operations/platform-slos.md`; benchmark regression budgets are intentionally separate. Saturation cannot be inferred from CPU alone and must combine Kubernetes, DataObs, and Elasticsearch signals.

## Backpressure and overload audit

| Path | Capacity / overflow / durability finding |
|---|---|
| Collection Manager | Not packaged; bounded scheduling and durable handoff evidence pending. |
| Scanner | Singleton; source-side paging/retries exist by connector, but aggregate queue bounds need evidence. |
| Monitors | Lease/checkpoint persistence exists; due-work backlog and retry saturation need measurement. |
| Stream intelligence | Not separately packaged; queue starvation and checkpoint-age evidence pending. |
| Incident runtime | Not separately packaged; reconciliation is durable in Elasticsearch, but overload limits need runtime evidence. |
| OpenLineage ingestion | HTTP ingestion is available; request-body, concurrency, and indexing backpressure must be measured. |
| Telemetry exporter | Collector queue configuration is deployment-specific; overflow and retry evidence pending. |

No path is certified as loss-free under overload by this audit. The harness therefore has finite duration, concurrency, operation count, per-request timeout, and error-rate circuit breaking. API reads in the scenario catalog are bounded resources; destructive administration and arbitrary Elasticsearch `_search`, scripts, wildcard searches, deep `from`, and unbounded aggregations are outside permitted load.
