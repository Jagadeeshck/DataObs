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
