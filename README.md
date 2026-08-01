# DataObs

Pathway Intelligence backend v1 provides metadata-only, tenant-scoped pathway
processing and canonical Elasticsearch APIs. See
[`docs/architecture/pathway-intelligence.md`](docs/architecture/pathway-intelligence.md),
[`docs/operations/pathway-worker.md`](docs/operations/pathway-worker.md), and
[`docs/operations/pathway-replay.md`](docs/operations/pathway-replay.md) for the
evidence, confidence, health, latency, and late-arrival contracts.

The console includes tenant-scoped Jobs inventory, Job 360, Run 360, run comparison, and a bounded dataset/column Lineage Explorer. Architecture and rebuild details are documented in `docs/architecture/lineage-projections.md` and `docs/operations/lineage-rebuild.md`.

## Status

DataObs is an **Elasticsearch-native Data Observability and Data Streams Monitoring product** under active development. **This repository is not a production release yet.** Capability and release-readiness claims are evidence-gated by the [capability ledger](docs/product/capability-ledger.yaml); local tests or the existence of configuration do not constitute hosted certification.

See the factual [current product baseline](docs/product/current-product-baseline.md), generated [feature matrix](docs/product/feature-matrix.md), and generated [evidence index](docs/product/evidence-index.md).

## Product architecture

Elasticsearch and Kibana are the authoritative storage and analysis platform. OpenTelemetry and OpenLineage are ingestion standards. Elastic Agent/Fleet/EDOT, the DataObs Scanner, PostgreSQL scanning, and Kafka observation provide implemented collection foundations; this does not imply universal connector support.

The backend exposes a bounded, tenant-authorized [OpenLineage ingestion contract](docs/architecture/openlineage-ingestion.md) and [canonical job/run projections](docs/architecture/job-run-observability.md). Platform normalizers reflect only the fixtures and evidence covered by this repository; they are not claims of universal Airflow, dbt, or Spark certification.

A React Console exists as the standalone **DataObs Console** and is the opinionated operational UI. Its implemented routes include Command Center, Flow, Assets, Pathways, Incidents, Streams, and Data Product list/detail views. A route is an implemented surface, not browser or accessibility certification.

The canonical target remains six pillars: **Platform**, **Data Pipeline**, **Data**, **FinOps and Cost**, **Business**, and **AI and Agent**. The latter differentiating pillars remain future scope unless the ledger records evidence otherwise.

## Current implementation

Data Product runtime foundations now include tenant-scoped product CRUD, membership proposals and decisions, dependency traversal, impact and revisions, reconciliation services, API routes, and Console list/detail routes. Automated monitoring, baselines, recommendations, quality execution, findings, deduplicated incidents, notification delivery persistence, and an OpenTelemetry quality-to-incident integration contract also exist. Their strongest supported state and remaining hosted-evidence blockers are recorded in the ledger.

The immutable Elasticsearch migration registry currently spans `0001` through `0021_lineage_analysis_explorer`. Released migrations must never be edited; forward corrections require a new additive migration.

## Development and evidence

The [certification and release gap audit](docs/development/certification-release-gap-audit.md) records the PR #171–#173 review and pending hosted actions.

The CI workflows define Python, migration/OCC, Elasticsearch 9.4.2, Data Product foundation and reconciliation, end-to-end signal-path, PostgreSQL, Kafka/OpenLineage, Console, browser/accessibility, infrastructure, image-security, and documentation gates. Final-head hosted runs and retained artifacts—not test files or local output—are required before promotion to `validated` or release-ready.
Focused certification is owned by `data-quality-monitoring`, `job-run-backend`, and `lineage-analysis-console`; each publishes an exact-commit artifact and has a separate download-and-verification job.

The production-representative signal-path contract is:

`quality check → OpenTelemetry → Collector → Elasticsearch → quality result → finding → deduplicated incident → Slack/PagerDuty/ServiceNow → redaction-safe delivery outcome → API retrieval`.

The workflow retains its evidence as `e2e-signal-path` when executed successfully.

## Deployment and releases

Compose, Kubernetes manifests, and a limited Helm foundation exist, but none establishes production readiness. The Helm chart currently covers only the API, quality worker, and an OpenTelemetry Collector foundation. Release images should be pinned to a semantic version, Git SHA, or digest; do not rely on `latest`.

POC, demo, and sample assets—including the Grafana Alloy sample application—are examples only and are not supported production runtime components.

## Documentation

- [Kafka observer architecture](docs/architecture/stream-observer.md)
- [Kafka observer operations](docs/operations/kafka-observer.md)
- [Current product baseline](docs/product/current-product-baseline.md)
- [Product documentation index](docs/product/README.md)
- [Architecture overview](docs/architecture/overview.md)
- [Evidence-gated roadmap](docs/product/roadmap-v1.md)
- [Certification harness](certification/README.md)
- [Local POC setup](docs/poc-setup.md)

## Safety boundary

Autonomous remediation is not enabled. Actions require explicit approval and safety controls, and no future-pillar capability is implied by this baseline.

### Stream 360 Core Console

The tenant-scoped `/streams`, Topic 360, and Consumer Group 360 investigation views document honest evidence states, accessible grid/table alternatives, safe configuration, URL-backed filtering, and cancellable refresh behavior. See [the operations guide](docs/operations/stream-360-console.md). Cluster, Connector, Schema, and Pathway redesigns are deferred.

### Kafka Cluster 360 Console

`/streams/clusters/:clusterId` now has a dedicated read-only operational console with bounded broker, topic, consumer-group and safe connector summaries plus evidence-based health. Missing observations remain unknown, changes/incidents report Not configured without providers, and optional 30-second polling pauses while hidden. See [the Cluster 360 operations guide](docs/operations/cluster-360-console.md).

## Parallel team delivery

Delivery governance is defined by [team ownership](docs/development/team-ownership.md), [GitHub development workflow](docs/development/github-delivery-conventions.md), the [ADR process](docs/architecture/adr/README.md), [migration ownership](docs/development/migration-ownership.md), the planned [Beta 1 delivery plan](docs/product/beta-1-delivery-plan.md), and the [certification evidence contract](docs/development/certification-evidence-contract.md). Beta 1 remains planned until hosted certification evidence supports promotion.

## Beta Kubernetes deployment package

The functional-but-unvalidated Beta chart is under [`helm/dataobs`](helm/dataobs/README.md). It packages runnable components against external Elasticsearch only; review the release manifest and Kubernetes production guides before evaluation.
