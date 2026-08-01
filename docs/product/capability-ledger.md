<!-- Generated from the machine-readable capability ledger. Do not edit manually. -->

# Capability ledger

Audited commit: `5164762a6337a44a76ad2c7574a78edc048a70b3` · PR range: #82-#168

## State counts

- **foundation**: 12
- **functional_unvalidated**: 18
- **not_started**: 6
- **optional_integration**: 1
- **scaffold**: 1

## Pillar counts

- **ai_agent**: 2
- **business**: 2
- **data**: 5
- **data_pipeline**: 9
- **finops_cost**: 1
- **platform**: 19

## Capabilities

### `future.advisor` — DataObs Advisor

Evidence-led status for dataobs advisor.

- **State:** `not_started`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `future.ai_agent` — AI and Agent Observability

Evidence-led status for ai and agent observability.

- **State:** `not_started`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `future.business` — Business Reliability Scorecards

Evidence-led status for business reliability scorecards.

- **State:** `not_started`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `monitoring.products` — Data Products, SLOs, Product 360, and RCA

Evidence-led status for data products, slos, product 360, and rca.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run foundation and full reconciliation profiles for the final PR head and independently verify retained artifacts.

### `data.asset360` — Asset Catalog and Asset 360

Evidence-led status for asset catalog and asset 360.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `data.postgres` — PostgreSQL discovery, schema, freshness, and profiling

Evidence-led status for postgresql discovery, schema, freshness, and profiling.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `data.quality_drift` — Quality and drift evidence

Evidence-led status for quality and drift evidence.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run the focused workflow for the final PR head and independently verify its retained exact-commit artifact.

### `monitoring.data_quality_console_v1` — Data Quality Console v1

Read-only quality overview, inventory, findings and Monitor 360 evidence.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-commit hosted evidence.

### `monitoring.runtime` — Monitor runtime, baselines, and recommendations

Evidence-led status for monitor runtime, baselines, and recommendations.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `data.pathways` — Lineage and Pathway Explorer

Evidence-led status for lineage and pathway explorer.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run the focused workflow for the final PR head and independently verify its retained exact-commit artifact.

### `pipeline.jobs` — Job and run domain and Explorer

Evidence-led status for job and run domain and explorer.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run the focused workflow for the final PR head and independently verify its retained exact-commit artifact.

### `streams.detail` — Stream 360 detail pages

Evidence-led status for stream 360 detail pages.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `pipeline.adapters` — Airflow, dbt, and Spark adapters

Evidence-led status for airflow, dbt, and spark adapters.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run the focused workflow for the final PR head and independently verify its retained exact-commit artifact.

### `pipeline.openlineage` — OpenLineage ingest

Evidence-led status for openlineage ingest.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run the focused workflow for the final PR head and independently verify its retained exact-commit artifact.

### `streams.connect_schema` — Kafka Connect and Schema Registry

Evidence-led status for kafka connect and schema registry.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `streams.connector_schema_360` — Connector and Schema 360 Console v1

Durable safe projections and read-only operational investigation.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Execute and independently verify the hosted workflow.

### `streams.kafka` — Kafka Observer and inventory

Evidence-led status for kafka observer and inventory.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `streams.live_actions` — Durable stream SSE and safe actions

Evidence-led status for durable stream sse and safe actions.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `future.finops` — FinOps and Cost Observability

Evidence-led status for finops and cost observability.

- **State:** `not_started`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `console.command` — Command Center

Evidence-led status for command center.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `console.validation` — Console browser and accessibility validation

Evidence-led status for console browser and accessibility validation.

- **State:** `scaffold`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `incidents.core` — Finding ingest, correlation, lifecycle, and timeline

Evidence-led status for finding ingest, correlation, lifecycle, and timeline.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run the final-head Elasticsearch 9.4.2 integration job and retain the redaction-safe e2e-signal-path artifact.

### `incidents.replay` — Incident mapping, OCC, and bounded replay

Evidence-led status for incident mapping, occ, and bounded replay.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `incidents.workbench` — Cases, workflows, approvals, actions, and verification

Evidence-led status for cases, workflows, approvals, actions, and verification.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `integration.cloud` — AWS, Azure, GCP, and Snowflake providers

AWS collector v2 is bounded and functional_unvalidated; Azure, GCP, and Snowflake remain deferred.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-commit hosted AWS v2 evidence.

### `integration.elastic` — Elasticsearch and Kibana authoritative plane

Evidence-led status for elasticsearch and kibana authoritative plane.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `integration.optional` — OpenSearch, Grafana, and Alloy interoperability

Evidence-led status for opensearch, grafana, and alloy interoperability. Elasticsearch remains authoritative; this is export/interoperability only.

- **State:** `optional_integration`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `integration.otel` — OpenTelemetry ingestion standard

Evidence-led status for opentelemetry ingestion standard.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run the final-head Elasticsearch 9.4.2 integration job and retain the redaction-safe e2e-signal-path artifact.

### `platform.architecture` — Elasticsearch-native architecture

Evidence-led status for elasticsearch-native architecture.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `platform.backup_restore` — Backup and restore

Evidence-led status for backup and restore.

- **State:** `not_started`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `platform.beta_deployment_package` — Beta deployment package

Digest-pinned Kubernetes packaging for runnable Beta components against external Elasticsearch.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-commit hosted packaging evidence.

### `platform.collection` — Collection manager

Evidence-led status for collection manager.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `platform.deployment` — Helm, Terraform, and release packaging

Evidence-led status for helm, terraform, and release packaging.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `platform.migrations` — Migration framework

Evidence-led status for migration framework.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain final-head migration/OCC and rolling-upgrade evidence from Elasticsearch 9.4.2.

### `platform.self_observability` — Self-observability

Evidence-led status for self-observability.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `platform.upgrades` — Rolling-upgrade correctness

Evidence-led status for rolling-upgrade correctness.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain final-head migration/OCC and rolling-upgrade evidence from Elasticsearch 9.4.2.

### `platform.iam` — OIDC and RBAC

Evidence-led status for oidc and rbac.

- **State:** `not_started`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `platform.tenancy` — Tenant model and boundaries

Evidence-led status for tenant model and boundaries.

- **State:** `foundation`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.
