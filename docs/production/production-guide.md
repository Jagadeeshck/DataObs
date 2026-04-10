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

---

## 5) AWS OTEL agent confirmation (EKS + EC2, metrics + logs + traces)

For AWS service telemetry collection, confirm your OpenTelemetry Collector (or ADOT Collector) has:

- `awscloudwatch` receiver connected to **metrics** and **logs** pipelines.
- `awsxray` (UDP 2000) or OTLP receiver connected to the **traces** pipeline.
- Valid AWS credentials from IAM role, IRSA, or environment variables.



### EC2 agent deployment option

For workloads running directly on EC2 (for example Spark driver/executor JVMs, Python ETL, or long-running services), run an OTEL collector **agent** on each host and forward data to your central collector/gateway.

- Use `config/otel-ec2-agent-config.yaml` as the baseline agent config.
- Use `infra/terraform/aws-ec2-otel-agent` to push install + config through AWS SSM to instance groups (tags) or individual nodes (instance IDs).
- It supports OTLP (`4317`/`4318`) for Java/Python instrumentation.
- It also supports AWS X-Ray daemon traffic on UDP `2000` via `awsxray` receiver.

Detailed runbook: [`docs/production/ec2-otel-agent.md`](ec2-otel-agent.md).

### Validation commands

```bash
# 1) Collector health
kubectl -n dataobs port-forward deploy/dataobs-otel-collector 13133:13133
curl -sf http://127.0.0.1:13133/

# 2) Collector self metrics (scrape confirmation)
kubectl -n dataobs port-forward deploy/dataobs-otel-collector 8888:8888
curl -s http://127.0.0.1:8888/metrics | grep -E "otelcol_receiver_accepted_(metric_points|log_records|spans)"

# 3) Data arriving in Elasticsearch
curl -u "$ELASTIC_USER:$ELASTIC_PASSWORD" "$ELASTIC_ENDPOINT/dataobs-metrics*/_count"
curl -u "$ELASTIC_USER:$ELASTIC_PASSWORD" "$ELASTIC_ENDPOINT/dataobs-logs*/_count"
curl -u "$ELASTIC_USER:$ELASTIC_PASSWORD" "$ELASTIC_ENDPOINT/dataobs-traces*/_count"
```

If metrics/logs increase but traces do not, verify AWS X-Ray traffic reaches UDP/2000 and security groups/network policies allow the flow.
