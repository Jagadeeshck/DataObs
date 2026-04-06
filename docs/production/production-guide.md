# DataObs Production Deployment Guide

This guide explains how to run DataObs in production while reusing your **existing OpenTelemetry** and **existing Elasticsearch** infrastructure.

## Deployment patterns

### Pattern A: Full DataObs stack
Use DataObs-managed OTEL Collector + Elasticsearch.

### Pattern B: Bring your own observability platform (recommended for enterprises)
Use your existing:
- OpenTelemetry Collector fleet (or vendor-managed OTEL)
- Elasticsearch cluster and Kibana space

DataObs then runs only product services (quality, lineage, alerting, API).

---

## 1) Configure existing OpenTelemetry infrastructure

In `config/dataobs.yaml`:

```yaml
deployment:
  telemetry_mode: external_otel

external_otel:
  enabled: true
  endpoint: "https://otel-gateway.company.net:4317"
  protocol: grpc
  tls_enabled: true
  headers:
    x-tenant-id: "data-platform"
```

### Notes
- Keep DataObs service names unique (`dataobs-quality`, `dataobs-api`).
- Reuse enterprise OTEL processors for resource tagging, masking, and routing.
- Enable trace/log correlation keys (`trace_id`, `span_id`) in pipelines.

---

## 2) Configure existing Elasticsearch cluster

```yaml
deployment:
  storage_mode: external_elasticsearch

elasticsearch:
  existing_cluster: true
  url: "https://es-prod.company.net:9200"
  username: "${ELASTICSEARCH_USER}"
  password: "${ELASTICSEARCH_PASSWORD}"
  verify_certs: true
  index_prefix: "dataobs-prod"
```

### Minimum index permissions
- create index
- write documents
- read/search on `dataobs-*`
- manage ILM on DataObs indices

---

## 3) Enable Elasticsearch ML support

DataObs can use native Elasticsearch ML jobs for anomaly detection (freshness spikes, row count drift, error bursts).

```yaml
ml:
  enabled: true
  engine: elasticsearch_native
  elasticsearch:
    use_native_ml: true
    start_jobs_on_bootstrap: false
    severity_threshold: 50
    jobs:
      - job_id: dataobs-freshness-age-anomaly
        enabled: true
      - job_id: dataobs-quality-rowcount-anomaly
        enabled: true
```

### Recommended rollout
1. Create jobs and datafeeds in monitor-only mode.
2. Review anomalies for 2–4 weeks.
3. Enable alerting only for high-confidence job scores.

---

## 4) Production hardening checklist
- Use secrets manager / vault for credentials.
- Set index lifecycle management (hot/warm/cold).
- Define SLOs per domain dataset.
- Configure ServiceNow and on-call channels.
- Enable backup/restore for DataObs index templates and saved objects.
