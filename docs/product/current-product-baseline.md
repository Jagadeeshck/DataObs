# Current product baseline

> Audit date: 2026-08-01. Integrated implementation baseline: `d3151937eeea88bb5c7bc4b4c71ab1d663347a4f`, including merged work through PR #205. This document records implemented capability, not hosted certification or production readiness.

## 1. Product identity

DataObs is a proprietary, Elasticsearch-native Data Observability and Data Streams Monitoring product owned by KJC InfoTech Limited. Elasticsearch and Kibana are authoritative storage and analysis components. OpenTelemetry and OpenLineage are ingestion standards, and the standalone DataObs Console is the operational UI.

The canonical six-pillar model remains the product target. A route, API, workflow or migration in the repository is not by itself proof of production readiness.

## 2. Target Elastic Stack

Certification definitions pin Elasticsearch and Kibana **9.4.2**. Compatibility with other versions is not certified by this baseline.

## 3. Storage migrations

The released forward-only migration registry spans `0001_product_foundation` through the executable terminal migration `0026_lineage_impact_change_intelligence`. Previously released migrations remain immutable; corrections require a new additive migration. Registry checksum validation and comparison against the audited branch base are mandatory release gates.

## 4. Streams and pathway observability

The Kafka Stream Observer supports bounded inventory, consumer-group offsets, optional Kafka Connect and Schema Registry collection, durable leases and checkpoints, capability-aware scheduling, canonical top-level projections, and explainable lag and retention intelligence.

The Console includes Streams Inventory, Topic 360, Consumer Group 360, Kafka Cluster 360, Connector 360 and Schema 360. These surfaces preserve measured-zero versus missing evidence, use bounded server-side filtering and pagination, and provide accessible table alternatives.

Pathway Intelligence supports durable event watermarks, overlap replay, fenced workers, canonical node and edge projections, bounded complete and partial pathway assembly, explainable health, latency and bottleneck calculations, comparison, and durable pathway SLO CRUD. Pathway Inventory and Pathway 360 are implemented.

The stream and pathway reliability runtime introduced by migration `0023_stream_pathway_reliability_runtime` evaluates tenant- and environment-scoped objectives with deterministic IDs, durable coordination, append-only evaluations, and explicit states including healthy, warning, breaching, recovering, no-data, stale, error and disabled. Its Console route is `/streams/reliability`.

All Team 1 capabilities remain `functional_unvalidated` until exact-commit Elasticsearch, Kafka, browser, accessibility and independent evidence verification completes.

## 5. Data quality, jobs and lineage

Data Quality Monitoring includes durable monitor definitions, schedules, leases, checkpoints, observations, baselines, evaluations, findings and run-now requests. The runtime uses fail-closed capability validation and tenant-scoped persistence.

The Console implements `/quality`, `/quality/monitors`, `/quality/monitors/new` and `/quality/monitors/:monitorId`. It includes overview, inventory, evidence, observations, evaluations, baselines, findings, incidents, suppressions, history, runtime status, capability-driven draft authoring, confirmed lifecycle operations, baseline reset, suppression creation and recommendation decisions. Missing evidence is not converted to zero, and autonomous remediation remains excluded.

OpenLineage ingestion validates, bounds and redacts incoming events before append-only persistence and projection into canonical jobs, runs, attempts, tasks and Spark stages. The Console includes Jobs Inventory, Job 360, Run 360, run comparison and bounded dataset and column lineage exploration. Lineage responses disclose confidence, evidence coverage, partial or missing state, cycle handling and truncation rather than inferring unobserved relationships.

These capabilities remain `functional_unvalidated` pending final-head Elasticsearch 9.4.2, PostgreSQL, browser, accessibility and independent-verification evidence.

## 6. Incidents and safe automation

The Incident Inbox and Incident Workbench are tenant- and environment-scoped. They use repository-side filtering, deterministic PIT and `search_after` pagination, signed filter-bound cursors, strict timeline storage adapters, append-only collaboration events, optimistic concurrency, idempotency keys and authenticated-principal actor attribution.

Incident correlation and alert-dispatch foundations exist, including deduplicated incident creation and redaction-safe Slack, PagerDuty and ServiceNow delivery outcomes. Unrestricted autonomous remediation is not supported. Full incident flood-control and storm-scale acceptance require a separate hosted evidence gate.

## 7. Integrations and collection

The provider-neutral Integration SDK defines typed capability, configuration, execution context, discovery, observation, checkpoint, retry, timeout, cancellation and redaction contracts. Collection Manager composes providers through durable checkpoint, observation and run repositories.

The AWS data-platform provider supports bounded, read-only collection for RDS and Aurora, Glue, Athena, EMR Serverless, S3, Lambda, SageMaker, MWAA, Redshift provisioned and Redshift Serverless, together with allowlisted CloudWatch metrics. Configuration v1 remains compatible with provider v2.

The AWS provider uses migration `0022_aws_data_platform_collector`; it is not the terminal migration. Live AWS certification remains pending, and Collection Manager does not yet have a supported packaged production workload or dedicated Docker image. AWS collection is therefore optional for the packaged Beta runtime.

The explicitly registered Snowflake provider generation 1 adds bounded account, warehouse, catalog, SQL-free query-history, load, metering-consumption, storage and metadata-freshness evidence. It reuses migration 0022 mappings and adds no migration. Its hosted suite has not run, so it remains `functional_unvalidated`; complete coverage, freshness, lineage, cost observability and production readiness are not claimed.

## 8. Console and product experience

The Console has a typed route registry that is the source of truth for route metadata, navigation, breadcrumbs, document titles, permissions, configuration state, lazy loading and entity links. Command Center, Unified Data Flow, Quick Find, tenant and environment context, time-range selection, global refresh, route error isolation, integrations catalogue and onboarding are implemented.

Implemented primary and detail routes cover Command Center, Flow, Assets, Pathways, Streams, Data Products, Data Quality, Jobs, Lineage, Incidents, Integrations and Onboarding. Final-head production build, Playwright and axe accessibility evidence remain mandatory release gates.

## 9. Identity and tenant security

OIDC resource-server validation, bounded JWKS handling, explicit service principals, durable Elasticsearch-backed role bindings, tenant- and environment-scoped authorization, method-aware deny-by-default route policy, IAM optimistic concurrency, security-event persistence, recursive redaction, CORS and browser security controls are implemented.

Local and focused tests do not replace hosted OIDC, tenant-isolation, key-rotation and production deployment proof. Evidence bundles must exclude tokens, authorization headers, webhook secrets, private keys and raw sensitive payloads.

## 10. Deployment and package coverage

The Beta Helm package covers components with supported Dockerfiles and entrypoints: API, Console, Quality Worker, Scanner Worker, Monitor Runtime, Pathway Worker, Kafka Observer, optional OpenTelemetry Collector and the migration Job. Elasticsearch remains external.

Collection Manager, embedded Elasticsearch, Kibana, identity providers, Grafana Alloy, demos and POCs are excluded from the supported package. Images must be pinned by semantic version, Git SHA or digest. Helm lint, rendering, Kind smoke, restart, upgrade and rollback evidence remain required.

## 11. End-to-end certification contracts

Defined contracts cover:

- quality check to OpenTelemetry, Elasticsearch, finding, incident and managed notification outcomes;
- Kafka and pathway collection and projection;
- OpenLineage job, run and lineage investigation;
- data-quality runtime and Console behavior;
- incident workbench OCC, idempotency, append semantics and redaction;
- OIDC, RBAC and tenant isolation;
- Helm deployment, restart, upgrade and rollback;
- snapshot backup and destructive restore;
- image build, SBOM, provenance and vulnerability scanning;
- cross-team Console build, browser and accessibility behavior.

Every promoted capability requires a retained exact-commit artifact and independent verification. Local output, test definitions or dry-run planning are not treated as hosted evidence.

## 12. Current release status and blockers

Beta 1 remains **NO_GO** until all mandatory gates pass for one frozen commit reachable from `main`.

Current blockers are:

- no complete set of successful retained exact-commit capability artifacts for the integrated final SHA;
- no completed integrated browser and accessibility matrix;
- incomplete hosted HA, restart, backup, restore, upgrade and rollback evidence;
- incomplete hosted OIDC and tenant-security evidence;
- incomplete image SBOM, provenance and vulnerability-scan evidence;
- Collection Manager is not a supported packaged workload;
- final release publication has not been approved and must remain disabled until certification passes.

## 13. Explicitly unsupported

FinOps, Business Observability, AI and Agent Observability, unrestricted custom providers, organisation-wide cloud crawling, raw payload inspection, unsupported SQL, destructive autonomous remediation, and POC or demo assets are not supported production capabilities in this baseline.

## 14. Next milestone

The next milestone is a clean integration repair followed by exact-commit Beta 1 certification against Elasticsearch 9.4.2. Development may continue after the repair branch is merged, but release status must remain blocked until the hosted evidence matrix is complete and independently verified.
