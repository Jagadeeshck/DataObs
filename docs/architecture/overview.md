# DataObs Architecture Overview

## Design Principles
1. **Open standards first:** OpenTelemetry as default instrumentation contract.
2. **Cloud agnostic:** run on AWS, Azure, GCP, or hybrid without platform lock-in.
3. **Fast onboarding:** declarative config and pre-built integrations.
4. **One correlation plane:** Elasticsearch indexes for infra, pipelines, quality, and lineage.

## Reference Architecture

1. **Collectors & agents**
   - OpenTelemetry Collectors ingest traces, logs, and metrics.
   - Optional custom receivers for data platforms (Glue, Airflow, dbt).

2. **Storage & search**
   - Elasticsearch stores:
     - `dataobs-metrics`
     - `dataobs-logs`
     - `dataobs-traces`
     - `dataobs-quality-results`
     - lineage node/edge indices

3. **DataObs core services**
   - Freshness monitor
   - Data quality checks
   - Lineage graph tracker
   - Alert manager (ServiceNow, PagerDuty, Slack, etc.)

4. **Visualization & workflows**
   - Kibana dashboards for engineering and leadership.
   - Alert handoff into ServiceNow incidents for ITSM workflows.

## Cloud Agnostic Deployment Modes
- Docker Compose (local sandbox)
- Kubernetes Helm-based deployment
- VM/hosted agent deployment

## Security and governance baseline
- Secret injection via environment variables or secret manager.
- Index lifecycle policies to control retention.
- Immutable audit logs for incidents and rule changes.
