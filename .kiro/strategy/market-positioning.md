---
inclusion: manual
---

# DataObs — Market Positioning and Competitive Context

> **Internal document. Do not reference any third-party product names in public-facing
> code, docs, or comments. Use the neutral language defined here.**

## What DataObs is

DataObs is an **Elasticsearch-native Data Observability and Data Streams Monitoring
platform** for engineering and data teams that need production-grade pipeline, stream,
quality, lineage, and incident intelligence — self-hosted in their own infrastructure,
backed by the full Elastic Enterprise feature set.

## The market problem we solve

The data observability market ($1.4B in 2025, growing toward $3.3B by 2035) is split
between:

**Expensive SaaS platforms** — strong ML-driven detection, mature UIs, broad connector
libraries. But: quote-only pricing typically in the $40K–$150K+/year range, data must
leave your environment, no stream/Kafka-native story, deep vendor lock-in.

**Open-source test runners** — zero license cost, maximum control. But: you write every
rule, no incident management, no stream observability, no integrated UI, significant
ongoing engineering effort.

**Full-stack APM vendors with data add-ons** — strong infra+APM integration. But:
$15–$30/host/month base plus data features billed per table ($15–$16/table/month),
40+ separately metered products, proprietary agent ecosystem.

**DataObs fills the gap**: the depth of an enterprise platform, self-hosted in your own
Elasticsearch cluster, with a transparent cost model (infrastructure only), using open
standards (OTLP, OpenLineage) rather than proprietary agents.

## Our differentiated position

### 1. Elasticsearch-native — not bolted on
Every quality finding, stream event, lineage record, incident, and migration lives in
Elasticsearch indices your team already knows. Results are queryable via ES|QL, Kibana
Discover, Watcher, and Kibana Lens — no proprietary query language to learn.

### 2. Enterprise Elastic license — features others can't use
With an Elastic Enterprise license we have access to:
- **Machine Learning / Anomaly Detection** (X-Pack ML) — unsupervised baseline learning
  on any metric time series without manual threshold authoring
- **Watcher** — rule-based alerting wired directly to our incident pipeline
- **Cross-cluster search / replication** — multi-environment observability from one pane
- **Field-level security and document-level security** — tenant isolation enforced at
  the storage layer, not just the API
- **Transform API** — continuous background aggregations for volume, freshness, and
  schema rollups without a separate scheduler
- **ESRE (Elasticsearch Relevance Engine)** — semantic/hybrid search across asset
  catalog and incident history
- **Canvas and Kibana dashboards** — zero-additional-cost operational views for data
  teams who already use Kibana
- **APM + Fleet** — direct integration with Elastic APM for pipeline-to-data correlation

### 3. Kafka and stream observability — native, not an afterthought
Stream and pathway intelligence is a first-class pillar. Kafka cluster inventory,
consumer-group offsets, lag intelligence, schema compatibility, pathway assembly,
capacity planning, and reliability SLOs are built into the core product, not an add-on.

### 4. OTLP and OpenLineage — open standards ingestion
Any OTel-instrumented pipeline emits directly to DataObs. Any OpenLineage-emitting
orchestrator (Airflow, dbt, Spark) sends lineage without a proprietary SDK. This means
integrations are community-maintained, not locked to our release cycle.

### 5. Self-hosted — your data stays yours
Metadata, quality signals, lineage, and incidents never leave your infrastructure.
For regulated industries (finance, healthcare, government) this is often non-negotiable.

### 6. Incident lifecycle depth
Rule-triggered findings → deduplicated incidents → OCC-safe append-only audit →
approval-bound notification delivery (Slack, PagerDuty, ServiceNow). No autonomous
remediation without explicit operator approval.

## Positioning statement (internal reference)

> DataObs is the open, Elasticsearch-native data observability platform for teams who
> need enterprise-grade stream, pipeline, quality, and incident intelligence —
> self-hosted in their own cluster, using open standards, at infrastructure cost.

## Key capability gaps to close (priority order)

| # | Gap | Elastic Enterprise capability that closes it |
|---|---|---|
| 1 | Automated anomaly detection without manual rules | X-Pack ML anomaly detection jobs on quality metrics |
| 2 | Built-in quality check templates (freshness, volume, null rate, schema drift) | ES Transform API for continuous rollups + Watcher for alerts |
| 3 | Asset catalog / discovery UI | ESRE semantic search + Kibana saved searches |
| 4 | dbt artifact ingestion | OpenLineage adapter + existing job/run pipeline |
| 5 | Multi-environment cross-cluster view | CCS (Cross-Cluster Search) |
| 6 | Broader quality source connectors | Integration SDK providers (Snowflake, BigQuery, Redshift) |
| 7 | Data contract authoring + enforcement | Elasticsearch index lifecycle + schema registry integration |

## Pricing model (target)

| Tier | Deployment | Cost model |
|---|---|---|
| Community | Self-hosted, basic license | Infrastructure only (Docker + ES basic) |
| Professional | Self-hosted, Enterprise license | Infrastructure + Elastic Enterprise license |
| Managed | Future: hosted offering | Per-environment/per-GB model TBD |

The Community tier (Elastic basic/free) covers: quality monitors, stream observer,
pathway intelligence, incidents, lineage, data products.

The Professional tier (Elastic Enterprise) adds: ML anomaly detection, Watcher-driven
alerting, field-level security, cross-cluster search, Transform rollups, ESRE catalog.
