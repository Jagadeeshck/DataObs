# DataObs — AWS Managed Grafana Setup Guide

This document covers how to connect DataObs to the AWS observability stack:
**Amazon Managed Grafana + Amazon Managed Prometheus (AMP) + Amazon OpenSearch Ingestion (OSIS)**.

---

## Architecture

```
Your Services
    │
    ▼ OTLP (gRPC/HTTP)
DataObs OTel Collector
    ├──► Elasticsearch 8.x + Kibana           (AIOps / ML — existing)
    │
    ├──► Amazon OpenSearch Ingestion (OSIS)
    │       ├── Traces  → OpenSearch Domain (trace-analytics-raw + service-map)
    │       └── Logs    → OpenSearch Domain (dataobs-logs-*)
    │
    ├──► Amazon Managed Prometheus (AMP)
    │       └── Metrics → via Prometheus Remote Write
    │                       + RED metrics from spanmetrics connector
    │
    └──► Amazon Managed Grafana
             ├── Data source: AMP (metrics)
             ├── Data source: Amazon OpenSearch Service (traces + logs)
             ├── Data source: AWS X-Ray (optional, for Lambda/ECS traces)
             └── Dashboards: Service maps, anomaly detection, drilldown correlations
```

---

## Prerequisites

- AWS account with permissions for `grafana:*`, `aps:*`, `osis:*`, `es:*`
- ADOT / OTel Collector running (this repo's `config/otel-collector-config.yaml`)
- IAM role for the collector with trust policy for EC2 / ECS / EKS

---

## Step 1 — Amazon Managed Prometheus (AMP)

### Create workspace

```bash
aws amp create-workspace \
  --alias dataobs-metrics \
  --region us-east-1
```

Copy the **workspace ID** (e.g. `ws-a1b2c3d4-...`) and set:

```bash
# In .env or ECS task definition / EC2 instance env:
AMP_REMOTE_WRITE_URL=https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-<id>/api/v1/remote_write
AWS_REGION=us-east-1
```

### IAM policy for collector

Attach this inline policy to your collector's IAM role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["aps:RemoteWrite"],
      "Resource": "arn:aws:aps:us-east-1:<account-id>:workspace/ws-<id>"
    }
  ]
}
```

The OTel Collector uses the `prometheusremotewrite/amp` exporter (already configured in
`config/otel-collector-config.yaml`) with `sigv4auth` — credentials come from IMDS automatically.

---

## Step 2 — Amazon OpenSearch Ingestion (OSIS)

### IAM: ingestion role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["osis:Ingest"],
      "Resource": "arn:aws:osis:us-east-1:<account-id>:pipeline/dataobs-otel"
    }
  ]
}
```

Attach to your collector's IAM role.

### Create OSIS pipeline

```bash
aws osis create-pipeline \
  --pipeline-name dataobs-otel \
  --min-units 1 \
  --max-units 4 \
  --pipeline-configuration-body file://config/aws/osis-pipeline.yaml \
  --region us-east-1
```

Set the ingestion endpoint:

```bash
OSIS_PIPELINE_ENDPOINT=https://dataobs-otel-<hash>.us-east-1.osis.amazonaws.com
```

### IAM: index write role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["es:ESHttpPost", "es:ESHttpPut", "es:ESHttpGet"],
      "Resource": "arn:aws:es:us-east-1:<account-id>:domain/dataobs-os/*"
    }
  ]
}
```

Set:

```bash
OSIS_INDEX_WRITE_ROLE_ARN=arn:aws:iam::<account-id>:role/DataObsOSISIndexRole
OPENSEARCH_AWS_DOMAIN_ENDPOINT=https://search-dataobs-os-<hash>.us-east-1.es.amazonaws.com
```

---

## Step 3 — Amazon Managed Grafana

### Create workspace

1. AWS Console → **Amazon Managed Grafana** → **Create workspace**
2. Name: `dataobs-grafana`
3. Authentication: SSO (IAM Identity Center) or SAML
4. Permissions: select the IAM role created above or let Grafana create one

### Add data sources

In the Grafana workspace → **Configuration** → **Data sources**:

#### Amazon Managed Prometheus (Metrics)

| Field | Value |
|---|---|
| Type | Amazon Managed Service for Prometheus |
| Name | DataObs AMP |
| Default | Yes |
| AWS Region | `us-east-1` |
| Workspace ID | `ws-<your-id>` |

Click **Save & Test** — should show "Data source is working".

#### Amazon OpenSearch Service (Traces)

| Field | Value |
|---|---|
| Type | Amazon OpenSearch Service |
| Name | DataObs OS Traces |
| URL | `https://search-<domain>.<region>.es.amazonaws.com` |
| Auth | AWS — SigV4 (uses workspace execution role) |
| Index | `trace-analytics-raw` |
| Time field | `@timestamp` |

#### Amazon OpenSearch Service (Logs)

| Field | Value |
|---|---|
| Type | Amazon OpenSearch Service |
| Name | DataObs OS Logs |
| URL | Same OpenSearch domain as above |
| Index | `dataobs-logs-*` |
| Log message field | `body` |
| Log level field | `attributes.log.level` |

#### AWS X-Ray (optional — Lambda / ECS traces)

AMG has native X-Ray integration — select **AWS X-Ray** data source type; auth is automatic via workspace role.

---

## Step 4 — Activate the backend

Set `DATAOBS_BACKEND=aws_grafana` on the OTel Collector:

```bash
# docker-compose
DATAOBS_BACKEND=aws_grafana docker compose up -d

# ECS / EC2 — update the environment variable in the task definition or service unit.
# The collector will activate metrics/amp and traces/opensearch_aws pipelines.
```

Or to send to ALL backends simultaneously:

```bash
DATAOBS_BACKEND=all docker compose up -d
```

---

## Step 5 — Import Dashboards

Pre-built dashboard JSON files are in `config/aws_grafana/dashboards/`:

| File | Purpose |
|---|---|
| `service-overview.json` | Service RED metrics (rate, error, duration) from AMP spanmetrics |
| `service-map.json` | Topology service map from OpenSearch Trace Analytics |
| `data-quality.json` | Quality engine rule results + lineage visualizations |
| `infrastructure.json` | Host metrics (system.cpu.*, system.memory.*, etc.) from AMP |

Import via Grafana UI: **Dashboards** → **Import** → upload JSON.

---

## OTel Semantic Conventions reference

All telemetry produced by DataObs follows OTel semconv. Key attributes:

| Attribute | Semconv path | Used for |
|---|---|---|
| `service.name` | `resource/service` | Service filtering in all backends |
| `service.version` | `resource/service` | Release correlation |
| `deployment.environment.name` | `resource/deployment-environment` | Env filtering (prod/staging) |
| `host.name` | `resource/host` | Host-level drilldown |
| `cloud.region` | `resource/cloud` | AWS region grouping |
| `k8s.namespace.name` | `resource/k8s` | Kubernetes namespace scope |
| `http.request.method` | `trace/http` | HTTP operation filtering |
| `http.response.status_code` | `trace/http` | Error rate by status |
| `db.system.name` | `trace/database` | Database type grouping |

Full reference: <https://opentelemetry.io/docs/specs/semconv/>
