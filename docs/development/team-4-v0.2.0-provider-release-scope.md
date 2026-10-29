# Team 4 v0.2.0 provider release scope

This matrix separates implementation, packaging, hosted fixture evidence, live-service evidence and the v0.2.0 support recommendation. Final support promotion remains Team 0-owned.

| Provider / path | Version | Main collection features | Runtime path | Packaged in v0.2.0 | Authentication | Hosted status reviewed | Live service proof | v0.2.0 decision | Key limitation |
|---|---:|---|---|---|---|---|---|---|---|
| Integration SDK | v1 contract | capabilities, retries, checkpoints, bounded provider execution | Collection Manager foundation | no standalone workload | provider-neutral | run 40671870750 pass | n/a | SUPPORTED_CANDIDATE foundation only | not a connector |
| OpenTelemetry ingestion | external Collector | OTLP traces/metrics/logs into DataObs telemetry path | bundled optional OTel Collector | yes, optional | exporter/backend credentials and TLS | packaging evidence owner-gated | final hosted package proof pending | OWNER_HANDOFF | Team 0 must validate/pin compatible upstream Collector image |
| OpenLineage ingestion | API contract | bounded/redacted OpenLineage run events | DataObs API | yes | DataObs authenticated API principal | Team 2 evidence required | endpoint path is not a provider live test | OWNER_HANDOFF | Team 2 semantics and Team 0 release evidence required |
| Kafka observation | Team 1 runtime | admin inventory, groups, offsets, optional Connect/Schema Registry | Kafka Observer | yes | Kafka TLS/SASL secret-backed configuration | stream-observer run 40671870669 failed | Kafka service was provisioned, but certification failed | OWNER_HANDOFF | Team 1/security failure must close |
| PostgreSQL scanner | Integration SDK provider v1 / legacy scanner 0.2.0 | metadata, schema, optional aggregate profiling | Scanner Worker | yes | referenced password, PostgreSQL TLS | run 40583054174 failed; workflow repaired on this branch | latest live job skipped | BLOCKED | packaged `run` path is heartbeat-only; lease manager is in-memory |
| AWS data platform/Kinesis/SQS | v3 | bounded AWS metadata/CloudWatch/messaging inventory | Collection Manager | no | AWS SDK chain/assume-role style read-only credentials | no current-main exact-SHA release run reviewed | no live AWS certification | EXPERIMENTAL | Collection Manager excluded from package |
| Google Pub/Sub | v1 (`gcp`) | topic/subscription metadata and allowlisted Monitoring metrics | Collection Manager | no | ADC, workload identity or impersonation | run 40671870728 pass | evidence says `not_run` | EXPERIMENTAL | no packaged runtime and no live GCP proof |
| RabbitMQ | v1 | vhost/queue/exchange/binding metadata and counters | Collection Manager | no | monitoring account, secret-referenced Basic auth/TLS | run 40671870655 pass | no retained live RabbitMQ certification | EXPERIMENTAL | no packaged runtime |
| Azure data platform | v1 | ADF, Synapse, ADLS metadata/metrics | Collection Manager | no | managed identity, workload identity or referenced service-principal secret | run 40671870703 pass | evidence says `not_run` | EXPERIMENTAL | no packaged runtime and no live Azure proof |
| Snowflake | v1 | warehouse/catalog/query-history-safe/load/usage metadata | Collection Manager | no | key-pair/OAuth/workload-style supported provider auth | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |
| Databricks | v1 | Unity Catalog, warehouses, jobs, bounded source-native evidence | Collection Manager | no | OAuth M2M / supported SDK auth | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |
| BigQuery | v1 | projects/datasets/tables/jobs/storage/reservations | Collection Manager | no | ADC, WIF, service-account impersonation | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |
| Trino | v1 | catalog/schema/relation/runtime/query metadata | Collection Manager | no | configured read-only engine credentials/TLS | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |
| Presto | v1 | catalog/schema/relation/runtime/query metadata | Collection Manager | no | configured read-only engine credentials/TLS | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |
| MySQL | v1 | relational metadata, schema, opt-in aggregate freshness/profiling | Collection Manager | no | referenced password and verified TLS | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |
| MariaDB | v1 | relational metadata, schema, opt-in aggregate freshness/profiling | Collection Manager | no | referenced password and verified TLS | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |
| SQL Server | v1 | relational metadata, schema, opt-in aggregate freshness/profiling | Collection Manager | no | provider-supported referenced credentials/TLS | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |
| Oracle | v1 | ALL_* metadata, schema, opt-in aggregate freshness/profiling | Collection Manager | no | referenced password, TCPS/server verification | no current-main exact-SHA release run reviewed | not demonstrated for release SHA | EXPERIMENTAL | no packaged runtime |

## Release rule

`SUPPORTED_CANDIDATE` in this document means Team 4 believes the path has enough implementation maturity to proceed to owner/final release certification. It is not a public support claim.

A provider can move out of `EXPERIMENTAL` only when the actual packaged runtime, auth path, least-privilege posture, restart/checkpoint behavior, exact-SHA hosted run and mandatory live-service test are all demonstrated.

For v0.2.0, Team 4 recommends **not** adding Collection Manager packaging merely to increase connector count. That is a future Team 0/package decision.


## Closure matrix — current release baseline

Current release baseline for this closure review: `f62acd9f0d32ec827c26b7c8ccc56b18ac0c9401`.

| Provider | Version | Implemented features | Packaged runtime | Live hosted test state | Exact-SHA certification state | Security boundary / limitation | v0.2.0 inclusion |
|---|---:|---|---|---|---|---|---|
| AWS | 3 | bounded metadata, metrics, health, Kinesis/SQS inventory | Collection Manager — not packaged | approved live release fixture not demonstrated | no exact-`f62acd9f` provider certification observed | read-only SDK/CloudWatch allowlists; no payload/object/SQL reads | EXCLUDED / EXPERIMENTAL |
| Snowflake | 1 | account/warehouse/catalog/query-history-safe/usage evidence | Collection Manager — not packaged | opt-in live harness exists; not demonstrated on release SHA | no exact-`f62acd9f` certification observed | fixed SQL, no arbitrary business-row collection | EXCLUDED / EXPERIMENTAL |
| Databricks | 1 | Unity Catalog, warehouses, jobs, bounded query/system evidence | Collection Manager — not packaged | opt-in harness requires approved synthetic workspace; not run | no exact-`f62acd9f` certification observed | OAuth M2M / read metadata; no arbitrary notebook/data reads | EXCLUDED / EXPERIMENTAL |
| BigQuery | 1 | projects, datasets, tables, jobs, storage, reservations | Collection Manager — not packaged | opt-in live harness exists; current tests explicitly skip without approved project | no exact-`f62acd9f` certification observed | metadata/viewer boundary; no arbitrary table-row reads | EXCLUDED / EXPERIMENTAL |
| GCP / Pub/Sub | 1 | topic/subscription metadata and Monitoring metrics | Collection Manager — not packaged | workflow evidence says live external fixture not run | run `40862724002` passed on `f62acd9f` but is not live certification | viewer/monitoring read-only; never pull/ack/publish | EXCLUDED / EXPERIMENTAL |
| Azure | 1 | ADF, Synapse, ADLS metadata/metrics | Collection Manager — not packaged | live Azure harness skipped without approved resources | run `40862724020` failed on `f62acd9f`; closure fix classifies schema discovery unsupported | management-plane read and bounded ADLS listing only; no content/SQL reads | EXCLUDED / EXPERIMENTAL |
| Trino | 1 | catalog/schema/relation/runtime/query metadata | Collection Manager — not packaged | opt-in disposable Trino harness exists; not release-certified | no exact-`f62acd9f` certification observed | fixed metadata/runtime queries; no arbitrary SQL API | EXCLUDED / EXPERIMENTAL |
| Presto | 1 | catalog/schema/relation/runtime/query metadata | Collection Manager — not packaged | opt-in disposable Presto harness exists; not release-certified | no exact-`f62acd9f` certification observed | HTTPS/host confinement and fixed metadata queries | EXCLUDED / EXPERIMENTAL |
| PostgreSQL | 1 | metadata, schema, health, optional aggregate freshness/profiling | Scanner Worker packaged, but durable scheduler path not proven | PR #314 live job skipped | contract run `40841108301` passed on `7201c4d5`; no live certification | read-only metadata and explicitly opted-in aggregates; no raw rows | EXCLUDED / BLOCKED |
| MySQL | 1 | metadata, schema, health, optional aggregate freshness/profiling | Collection Manager — not packaged | opt-in live contract exists; no release live proof | no exact-`f62acd9f` certification observed | verified TLS, local infile disabled, no raw rows/query history | EXCLUDED / EXPERIMENTAL |
| MariaDB | 1 | metadata, schema, health, optional aggregate freshness/profiling | Collection Manager — not packaged | opt-in live contract exists; no release live proof | no exact-`f62acd9f` certification observed | Connector/C dependency, verified TLS, no raw rows/query history | EXCLUDED / EXPERIMENTAL |
| SQL Server | 1 | metadata, schema, health, optional aggregate freshness/profiling | Collection Manager — not packaged | opt-in SQL Server 17/16 harness exists; not run | no exact-`f62acd9f` certification observed | strict/mandatory TLS; no Query Store/raw rows | EXCLUDED / EXPERIMENTAL |
| Oracle | 1 | ALL_* metadata, schema, health, optional aggregate freshness/profiling | Collection Manager — not packaged | approved 26ai/19c live services absent; tests skip | no exact-`f62acd9f` certification observed | TCPS/server verification; no AWR/ASH/raw rows | EXCLUDED / EXPERIMENTAL |
| RabbitMQ | 1 | vhost/exchange/queue/binding metadata and counters | Collection Manager — not packaged | external HTTPS RabbitMQ fixture is opt-in; no live retained release proof | run `40862723981` passed on `f62acd9f`, fixture/contract only | monitoring-only account; no consume/basic.get/message bodies | EXCLUDED / EXPERIMENTAL |

### Supported-set recommendation

Team 4 recommends **zero Team 4 provider connectors as supported in v0.2.0**.

This is intentional. The Integration SDK can be certified as a foundation, but the cloud/warehouse/database/messaging providers that use Collection Manager are not operationally packaged. PostgreSQL has a packaged Scanner Worker image but not a demonstrated durable distributed scheduler/lease/fencing path.

The release may still include OpenTelemetry, OpenLineage and Kafka collection/ingestion capabilities if Team 0, Team 2 and Team 1 respectively provide exact-release-SHA runtime/package certification. Those are owner-gated product paths, not Team 4 provider promotions.


## Sprint 3 provider certification closure

Audited release baseline: `855345eb02250f9a738abe44bd520247243032bf`.

Team 0's current release authority remains authoritative: DataObs v0.2.0 is **NO_GO**, no supported platform is published, and rc.1 must not be promoted until one exact SHA reaches `GATE_0_GREEN` with independently verified mandatory evidence.

### Evidence categories used in this matrix

- **PACKAGED_AND_CERTIFIED** — runtime is in the supported package and exact-SHA live/runtime certification is independently verified.
- **IMPLEMENTED_UNVALIDATED** — implementation and hosted contract/fixture tests exist, but live provider/runtime certification or packaging is incomplete.
- **EXPERIMENTAL** — implementation exists but has weaker/current-SHA evidence, optional dependencies/environment constraints, or no current release certification.
- **EXCLUDED** — intentionally outside the v0.2.0 supported connector boundary.

No Team 4 provider currently qualifies as `PACKAGED_AND_CERTIFIED`.

| Provider | Version | Implemented collection | Packaged runtime | Current hosted evidence | Live provider evidence | Credential / least-privilege boundary | Sprint 3 classification | v0.2.0 support decision |
|---|---:|---|---|---|---|---|---|---|
| AWS | 3 | bounded metadata/metrics plus Kinesis/SQS inventory | Collection Manager; excluded from supported Helm package | historical provider workflows only; AWS is optional in Team 0 certification manifest | no release-SHA live AWS proof | SDK/assume-role style credentials, allowlisted read APIs/CloudWatch; no message or database payload reads | EXPERIMENTAL | EXCLUDED |
| Snowflake | 1 | account, warehouse, catalog, SQL-free query history, usage/load evidence | Collection Manager; not packaged | fixture/contract implementation exists | opt-in approved sandbox not release-certified | secret-referenced key/OAuth/workload auth; fixed SQL and no business-row collection | EXPERIMENTAL | EXCLUDED |
| Databricks | 1 | Unity Catalog, warehouse, job/run and bounded system evidence | Collection Manager; not packaged | fixture/contract implementation exists | approved OAuth workspace live proof not retained for release | OAuth M2M; bounded metadata/system evidence, no arbitrary notebook/data reads | EXPERIMENTAL | EXCLUDED |
| BigQuery | 1 | projects, datasets, tables, jobs, storage, reservations | Collection Manager; not packaged | fixture/contract implementation exists | approved synthetic project live proof absent | ADC/WIF/impersonation; no arbitrary table-row reads | EXPERIMENTAL | EXCLUDED |
| GCP / Pub/Sub | 1 | topic/subscription metadata and allowlisted Monitoring metrics | Collection Manager; not packaged | supplied pass `40869888236`; current-main pass `40961601012` | live external Pub/Sub fixture is opt-in and not certified by these passes | viewer/monitoring read access; never pull, ack, seek or publish | IMPLEMENTED_UNVALIDATED | EXCLUDED |
| Azure | 1 | ADF, Synapse and ADLS metadata/metrics | Collection Manager; not packaged | supplied pass `40869888478`; current-main pass `40961601165` | approved synthetic Azure live test not established by hosted contract pass | managed/workload identity or referenced SP secret; management-plane reads and bounded ADLS listing only | IMPLEMENTED_UNVALIDATED | EXCLUDED |
| Trino | 1 | catalog/schema/relation plus bounded runtime/query metadata | Collection Manager; not packaged | implementation/contract evidence exists | disposable Trino live proof not retained for release SHA | verified TLS/secret refs; fixed metadata/runtime statements, no arbitrary SQL | EXPERIMENTAL | EXCLUDED |
| Presto | 1 | catalog/schema/relation plus bounded runtime/query metadata | Collection Manager; not packaged | implementation/contract evidence exists | disposable Presto live proof not retained for release SHA | HTTPS authority confinement, secret refs and fixed metadata statements | EXPERIMENTAL | EXCLUDED |
| PostgreSQL | 1 | metadata/schema plus opt-in aggregate freshness/profiling | Scanner Worker is packaged | PR #314 contract run `40841108301` passed Python 3.11/3.12 | live PostgreSQL job skipped | secret references, verified TLS/read-only metadata; raw rows excluded | IMPLEMENTED_UNVALIDATED / BLOCKED | EXCLUDED |
| MySQL | 1 | metadata/schema plus opt-in aggregate freshness/profiling | Collection Manager; not packaged | implementation/contract evidence exists | live fixture not release-certified | referenced secret, verified TLS, local infile disabled, no raw rows/query history | EXPERIMENTAL | EXCLUDED |
| MariaDB | 1 | metadata/schema plus opt-in aggregate freshness/profiling | Collection Manager; not packaged | implementation exists; native Connector/C remains an environment dependency | live fixture not release-certified | referenced secret, verified TLS, no raw rows/query history | EXPERIMENTAL | EXCLUDED |
| SQL Server | 1 | metadata/schema plus opt-in aggregate freshness/profiling | Collection Manager; not packaged | implementation/contract evidence exists | SQL Server 17/16 live fixture not release-certified | secret refs; strict/mandatory TLS; no Query Store/raw row collection | EXPERIMENTAL | EXCLUDED |
| Oracle | 1 | ALL_* structural metadata plus opt-in aggregate freshness/profiling | Collection Manager; not packaged | implementation/contract evidence exists | approved 26ai/19c services not release-certified | secret refs, TCPS/server verification; no AWR/ASH/raw rows | EXPERIMENTAL | EXCLUDED |
| RabbitMQ | 1 | vhost/exchange/queue/binding metadata and counters | Collection Manager; not packaged | supplied pass `40869888078`; current-main pass `40961601051` | external HTTPS RabbitMQ fixture is opt-in; contract pass is not live certification | monitoring-only credentials; no consume/basic.get/publish/message bodies | IMPLEMENTED_UNVALIDATED | EXCLUDED |

### PostgreSQL packaged-runtime assessment

The contract suite is healthy, but the package is not operationally certifiable as a supported scanner:

- Helm starts `python -m services.scanner_worker.cli --config ... run`.
- The current `run` path is heartbeat-oriented and does not provide a demonstrated durable distributed task scheduler.
- `ScannerWorker` defaults to `InMemoryLeaseManager`, explicitly a development/test implementation.
- No packaged durable lease/fencing store, restart-safe task acquisition loop, or independently verified failover/restart path is present.

For v0.2.0, Team 4 chooses the bounded option: PostgreSQL remains excluded instead of adding a new scheduler/control plane during release closure.

### First-release Team 4 recommendation

**Supported Team 4 provider connectors: none.**

The Integration SDK is a mandatory release foundation, not a provider support claim. Pub/Sub, Azure and RabbitMQ hosted passes prove their current contracts remain healthy, but all three still execute through Collection Manager, which Team 0 explicitly excludes from the supported package. PostgreSQL is packaged but lacks the durable production scheduling/lease evidence required for a support claim.
