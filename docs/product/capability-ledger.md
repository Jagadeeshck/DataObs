<!-- Generated from the machine-readable capability ledger. Do not edit manually. -->

# Capability ledger

Audited commit: `5164762a6337a44a76ad2c7574a78edc048a70b3` · PR range: #82-#168

## State counts

- **foundation**: 12
- **functional_unvalidated**: 37
- **not_started**: 6
- **optional_integration**: 1
- **scaffold**: 1

## Pillar counts

- **ai_agent**: 2
- **business**: 2
- **data**: 9
- **data_pipeline**: 21
- **finops_cost**: 1
- **platform**: 22

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

### `data.mariadb` — MariaDB database collector v1

Safe structural MariaDB metadata and policy-owned aggregate evidence.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run and independently verify the hosted workflow against MariaDB 11.8 LTS and 11.4 LTS.

### `data.mysql` — MySQL database collector v1

Safe structural MySQL metadata and policy-owned aggregate evidence.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run and independently verify the hosted exact-commit workflow against MySQL 8.4 LTS.

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

Evidence-aware quality investigation with bounded authoring and safe mutations.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-commit hosted evidence.

### `monitoring.data_slo` — Data Quality SLOs, Error Budgets and Burn Rate

Canonical Team 2 asset and job SLI, error-budget, burn-rate, and Data Product child-roll-up semantics.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Complete the production vertical slice and independently verify its retained exact-head artifact.

### `monitoring.runtime` — Monitor runtime, baselines, and recommendations

Evidence-led status for monitor runtime, baselines, and recommendations.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Execute and retain the evidence required for promotion.

### `quality.asset_trust` — Asset Trust and Reliability Score

Explainable asset-level aggregation of canonical reliability and observability evidence.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Add the forward migration and complete API, Console, ES 9.4.2, browser, axe, scale, and independent exact-head certification.

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

### `pathways.pathway_before_after_compare_v1` — Pathway before/after comparison v1

Bounded evidence-led pathway investigation; no root-cause claim.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-SHA hosted evidence.

### `pathways.pathway_blast_radius_v1` — Pathway blast radius v1

Bounded evidence-led pathway investigation; no root-cause claim.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-SHA hosted evidence.

### `pathways.pathway_bottleneck_analysis_v1` — Pathway bottleneck analysis v1

Bounded evidence-led pathway investigation; no root-cause claim.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-SHA hosted evidence.

### `pathways.pathway_investigation_evidence_v1` — Pathway investigation evidence v1

Bounded evidence-led pathway investigation; no root-cause claim.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-SHA hosted evidence.

### `pathways.pathway_time_travel_v1` — Pathway time travel v1

Bounded evidence-led pathway investigation; no root-cause claim.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-SHA hosted evidence.

### `streaming.anomaly_retention_intelligence_v1` — Stream anomaly, retention and failure intelligence v1

Explainable tenant-scoped anomaly baselines, retention forecasts and metadata-only failure candidates.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Complete API/runtime/Resource 360 closure and retain independently verified exact-commit hosted evidence.

### `data_pipeline.stream_pathway_reliability` — Stream and pathway reliability runtime v1

Tenant-scoped bounded reliability evaluation without root-cause or remediation claims.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and verify the focused workflow artifact for the final commit.

### `streams.capacity_headroom_v1` — Capacity headroom v1

Evidence-first provider-neutral stream capacity semantics.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify hosted exact-SHA Elasticsearch and scale evidence.

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

### `streams.consumer_capacity_v1` — Consumer capacity v1

Evidence-first provider-neutral stream capacity semantics.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify hosted exact-SHA Elasticsearch and scale evidence.

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

### `streams.partition_shard_pressure_v1` — Partition shard pressure v1

Evidence-first provider-neutral stream capacity semantics.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify hosted exact-SHA Elasticsearch and scale evidence.

### `streams.retention_planning_v1` — Retention planning v1

Evidence-first provider-neutral stream capacity semantics.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify hosted exact-SHA Elasticsearch and scale evidence.

### `streams.saturation_intelligence_v1` — Saturation intelligence v1

Evidence-first provider-neutral stream capacity semantics.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify hosted exact-SHA Elasticsearch and scale evidence.

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

### `incidents.recurrence_similarity_intelligence` — Recurrence and Similar Incident Intelligence v1

Deterministic evidence-first incident fingerprints, bounded historical candidate retrieval, explainable similarity, and candidate recurrence semantics.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Complete the production vertical slice and certify against Elasticsearch 9.4.2 and the Console.

### `integration.cloud` — Cloud, warehouse, and RabbitMQ providers

AWS v3, Snowflake v1, and RabbitMQ Management HTTP API v1 are bounded and functional_unvalidated; hosted RabbitMQ 4.3.x evidence is pending.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain and independently verify exact-commit hosted AWS v2 and Snowflake v1 evidence.

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

### `integration.presto` — Presto SQL engine collector v1

Independent PrestoDB provider with bounded metadata and runtime evidence over the shared SQL-engine foundation.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Run and independently verify the hosted exact-commit workflow with disposable Presto.

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

### `platform.environment_tenant_multicluster_lifecycle_v1` — Environment tenant and multi-cluster lifecycle v1

Deterministic metadata-only registries, lifecycle state machines, staged tenant offboarding, fleet drift and release skew.

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Retain exact-SHA two-cluster lifecycle, failure, upgrade, rollback, isolation and recovery evidence.

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

### `streams.capacity_planning_v1` — Stream capacity planning v1

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify hosted exact-SHA API, scale, Playwright, and axe evidence.

### `streams.capacity_forecast_v1` — Stream capacity forecast v1

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify retained forecast accuracy evidence.

### `streams.capacity_recommendations_v1` — Advisory capacity recommendations v1

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify provider safety evidence.

### `streams.capacity_what_if_v1` — Bounded capacity what-if v1

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Verify scenario isolation evidence.

### `pathways.capacity_bottleneck_overlay_v1` — Pathway capacity overlay v1

- **State:** `functional_unvalidated`
- **Release readiness:** `blocked`
- **Next gate:** Complete and certify Pathway 360 presentation.
