---
inclusion: always
---
# DataObs — product vision

DataObs is an **Elasticsearch-native Data Observability + Data Streams Monitoring platform**. Build one integrated product that moves from telemetry and lineage ingestion to trustworthy data/stream health, causal investigation, SLOs, incidents, business context, and eventually explainable assisted operations.

## Users / value
- Platform and SRE teams: fleet, pipelines, stream throughput, lag, infrastructure, reliability and ownership.
- Data engineers: quality failures, job/run health, lineage, freshness, source/target dependencies and root-cause evidence.
- Data product owners: trust, service levels, impact, business-critical datasets, consumers and costs.
- Operations/on-call: actionable incidents, deduplication, explanations and **approval-bound** response.

## Six product pillars
1. **Platform Observability** — Elasticsearch, Kafka, databases, cloud runtime, capacity and platform service health.
2. **Data Pipeline Observability** — end-to-end ingestion, Kafka streams/pathways, jobs/runs, OpenLineage, checkpoint/replay, throughput/failures.
3. **Data Observability** — schema, data quality, volume/freshness/distribution, data products, lineage, reliability and trust.
4. **FinOps & Cost Observability** — attributable pipeline/asset/tenant costs, efficiency, forecasting (future unless evidence proves otherwise).
5. **Business Observability** — business-impact journeys and consumer-facing SLOs (future unless evidence proves otherwise).
6. **AI & Agent Observability** — traceable assisted investigation, explainability, human-approved operations (future unless evidence proves otherwise).

## Product promise
A tenant can understand: **what failed, where, when, which assets/consumers were impacted, how confident the evidence is, and what safe action is possible**. Show missing/stale/unknown separately from a measured zero. Avoid claims stronger than collected evidence.

## Product foundations
Elasticsearch/Kibana are analysis/storage authorities. OpenTelemetry and OpenLineage are primary ingestion standards. Use the existing React DataObs Console; do not replace it with a disconnected dashboard. Integrations are capability-qualified, not universally supported.

## Roadmap discipline
Deliver in layers: (A) secure and deployable platform, (B) streams/pipelines/quality/jobs/lineage/incidents, (C) product trust and integrated UX, (D) cost/business intelligence, (E) AI-assisted workflows. **First release this week is a bounded, certifiable subset, not all six pillars.**

Read current `README.md`, `docs/product/capability-ledger.yaml`, `docs/product/current-product-baseline.md` and `docs/kiro/PRODUCT-VISION-AND-ROADMAP.md`; if conflicts occur, trace the live code and evidence and raise the discrepancy.
