# DataObs Four-Pillar (Tower) Product Model

DataObs uses a **four-pillar architecture** so teams can adopt observability incrementally while keeping one unified platform.

## Pillar 1: Full-Stack Observability
**Goal:** monitor infrastructure and runtime behavior.

**Coverage**
- Hosts, containers, Kubernetes nodes/pods
- API/application latency and traces
- Logs and exception rates

**OpenTelemetry usage**
- OTLP traces + metrics + logs from all services
- Resource attributes for cloud provider, service, and environment

## Pillar 2: Pipeline Observability
**Goal:** ensure pipelines complete on time and reliably.

**Coverage**
- Batch jobs (Glue, Spark/EMR, Airflow)
- Streaming jobs (Kafka/Kinesis)
- CI/CD data deployment pipelines

**Signals**
- SLA breaches
- Retry/failure rates
- Runtime/cost drift

## Pillar 3: Data Observability
**Goal:** ensure data is fresh, complete, accurate, and trusted.

**Coverage**
- Freshness per table/topic
- Validation checks (nulls, ranges, uniqueness, RI)
- Schema drift
- End-to-end lineage and impact analysis

## Pillar 4: Business Observability
**Goal:** connect technical incidents to business outcomes.

**Coverage**
- KPI health tracking
- Revenue/operations impact estimation
- Executive scorecards

## Why this model works
- It mirrors successful patterns from tools like Datadog, Dynatrace, Splunk, and Monte Carlo while keeping DataObs **open and cloud-agnostic**.
- It supports phased rollout: start with Full-Stack + Pipeline, then add Data + Business observability.
- It provides a single telemetry language through OpenTelemetry and a single analytical backend in Elasticsearch.
