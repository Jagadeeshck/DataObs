# DataObs POC — Setup & Run Guide

> **Elastic Stack version:** 9.3.3 (latest, April 2026)
> **APM:** Built into Elasticsearch 9.x via Elastic Agent — no separate `apm-server` container needed.

This guide gets the DataObs Proof-of-Concept running end-to-end in **under 10 minutes** using three dedicated files:

| File | Purpose |
|---|---|
| `.env.poc` | All environment variables for the POC stack |
| `config/dataobs_poc.yaml` | Full POC pipeline configuration |
| `docker-compose.poc.yml` | Self-contained Docker stack |

No changes to the main `docker-compose.yml` or `config/dataobs.yaml` are needed.

---

## Architecture

```
 data.gov.uk (CKAN API)
       | auto-discovered CSV/JSON datasets
       v
 +---------------------+    OTLP/HTTP     +----------------------+
 |  pipeline container |----------------->|  otel-collector:4318 |
 |  (PySpark + Python) |                  +----------+-----------+
 +----------+----------+                             |
            |                           +-----------+-------------+
            | bulk index                |                         |
            v                    traces v              metrics/logs v
 +--------------------+   +---------------------+   +---------------------+
 | dataobs-poc-raw    |   | elastic-agent :8200  |   | Elasticsearch :9200  |
 | dataobs-poc-curated|   | (APM Server 9.x)     |   | dataobs-poc-telemetry|
 | dataobs-poc-quality|   +----------+----------+   +----------+----------+
 | dataobs-poc-lineage|              |                          |
 +--------------------+              v                          |
                         +---------------------+                |
                         |   Elasticsearch     |<---------------+
                         |   traces-apm-*      |
                         |   metrics-apm-*     |
                         |   logs-apm-*        |
                         +----------+----------+
                                    |
                                    v
                         +---------------------+
                         |   Kibana :5601       |
                         |   Observability/APM  |
                         |   Custom dashboards  |
                         +---------------------+
```

### Why no separate `apm-server` container?

In **Elastic Stack 9.x**, APM Server is no longer a standalone service. It is managed by **Elastic Agent** via Fleet Server and runs as an integrated process. The APM intake endpoint (`http://elastic-agent:8200`) speaks both the Elastic APM protocol and native **OTLP over gRPC/HTTP**. Traces sent by the OTel Collector land in the `traces-apm-*` data streams and appear in **Kibana → Observability → APM**.

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Docker | 24+ |
| Docker Compose | v2 (`docker compose`) |

No Python, Java, or Spark installation needed on your machine — everything runs inside Docker.

**Memory:** Allocate at least **6 GB RAM** to Docker for the full stack (ES + Kibana + Fleet + Agent + OTel + pipeline).

---

## Step-by-step

### 1 — Copy the env file

```bash
cp .env.poc .env.poc.local
```

The defaults work out of the box. Edit `.env.poc.local` only if you want non-default passwords.

> ⚠️ `.env.poc.local` is gitignored. Never commit it.

### 2 — Start the infrastructure stack

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  up -d elasticsearch kibana fleet-server elastic-agent otel-collector
```

Service startup order (automatic via `depends_on` + healthchecks):

```
elasticsearch  ->  es-setup  ->  kibana
                            ->  fleet-server  ->  elastic-agent
                                                        |
                                               otel-collector
```

Wait until all services are healthy (~60–90 s on first pull):

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local ps
# All should show: Status: healthy
```

### 3 — Run the pipeline

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  run --rm pipeline
```

The pipeline will:
1. **Discover** 3 public datasets from data.gov.uk (transport, environment, government)
2. **Download** each CSV/JSON file
3. **Parse & transform** with PySpark
4. **Quality-check** each dataset (row count, null %, duplicates, schema)
5. **Index** raw, curated, quality, and lineage docs into Elasticsearch
6. **Emit OTel traces** → OTel Collector → Elastic Agent APM (visible in Kibana APM)
7. **Emit OTel metrics/logs** → OTel Collector → Elasticsearch directly
8. **Bootstrap** Kibana data views and 3 custom dashboards

Typical run time: **3–6 minutes**.

### 4 — Open Kibana

Navigate to **http://localhost:5601**
- **Username:** `elastic`
- **Password:** value of `ELASTIC_PASSWORD` in `.env.poc.local` (default: `dataobs_poc_secret`)

---

## What you’ll see in Kibana

### Observability → APM → Services
The `dataobs-poc-pipeline` service appears here with:
- Full **distributed traces** for each pipeline stage (discover, download, parse, transform, quality_check, load_elasticsearch)
- **Stage duration** histograms and latency percentiles
- **Error tracking** (any failed stages appear as APM errors)
- **Trace waterfall** view showing stage-by-stage span breakdown

### Analytics → Dashboards

| Dashboard | What you’ll see |
|---|---|
| **[DataObs POC] Pipeline Health** | Stage durations, records ingested, OTel metrics |
| **[DataObs POC] Data Quality Overview** | Null %, duplicate ratio, row counts, pass/warn/fail |
| **[DataObs POC] Public Dataset Explorer** | Browse road safety, air quality, local authority data |

### Discover

| Data view | Index / data stream |
|---|---|
| `dataobs-poc-curated*` | Spark-processed dataset records |
| `dataobs-poc-quality*` | Quality check results |
| `dataobs-poc-lineage*` | Lineage events |
| `dataobs-poc-telemetry-metrics*` | OTel metrics (stage duration, record count) |
| `dataobs-poc-telemetry-logs*` | Pipeline structured logs |
| `traces-apm*` | APM distributed traces |
| `metrics-apm*` | APM metrics |
| `logs-apm*` | APM logs |

---

## Tear down

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local down -v
```

---

## Configuration reference

All POC settings live in **`config/dataobs_poc.yaml`**. Key sections:

### Pin specific datasets (skip CKAN auto-discovery)

```yaml
poc:
  data_sources:
    - name: my-dataset
      source_type: custom
      resource_url: "https://example.com/data.csv"
      format: csv
```

### Change quality thresholds

```yaml
poc:
  processing:
    quality_rules:
      max_null_pct_warn: 10.0
      max_null_pct_fail: 30.0
      duplicate_threshold_pct: 2.0
```

### Point at AWS OpenSearch instead of local ES

In `.env.poc.local`:
```bash
ELASTICHOST=https://your-domain.eu-west-1.es.amazonaws.com
ELASTIC_PASSWORD=your-master-password
```

Then skip local ES and Fleet services:
```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  up -d kibana otel-collector
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  run --rm pipeline
```

---

## Resource requirements

| Service | RAM (approx) |
|---|---|
| Elasticsearch 9.3.3 | 1.5 GB |
| Kibana 9.3.3 | 1 GB |
| Fleet Server | 256 MB |
| Elastic Agent (APM) | 512 MB |
| OTel Collector | 256 MB |
| Pipeline (PySpark) | 1 GB |
| **Total** | **~4.5–6 GB** |

> Allocate at least **6 GB RAM** to Docker in Docker Desktop preferences.

---

## Elasticsearch indices & data streams

| Index / data stream | Content |
|---|---|
| `dataobs-poc-raw` | Raw parsed records |
| `dataobs-poc-curated` | Spark-normalised records |
| `dataobs-poc-quality` | Quality check results |
| `dataobs-poc-lineage` | Lineage events |
| `dataobs-poc-telemetry-metrics` | OTel pipeline metrics |
| `dataobs-poc-telemetry-logs` | Pipeline structured logs |
| `traces-apm-*` | Distributed traces (Kibana APM) |
| `metrics-apm-*` | APM service metrics |
| `logs-apm-*` | APM log correlation |
