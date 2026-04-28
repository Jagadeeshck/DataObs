# DataObs POC — Setup & Run Guide

> **Elastic Stack:** 9.3.3 (latest stable, April 2026)
> **APM Server:** Built into Elasticsearch 9.x via Elastic Agent — **no separate `apm-server` container**.

This guide gets DataObs running end-to-end locally in **under 10 minutes** using three dedicated files that don't touch the main stack config at all:

| File | Purpose |
|---|---|
| `.env.poc` | All environment variables for the POC stack |
| `config/dataobs_poc.yaml` | Full POC pipeline & APM configuration |
| `docker-compose.poc.yml` | Self-contained Docker stack (7 services) |

---

## Architecture

```
 data.gov.uk (CKAN API)
        │  auto-discovered CSV/JSON datasets
        ▼
 +--------------------+   OTLP/HTTP    +----------------------+
 | pipeline container |───────────────►| otel-collector :4318 |
 | (PySpark + Python) |                +----------+-----------+
 +--------+-----------+                           │
          │                        ┌──────────────┼──────────────┐
          │ bulk index         traces           metrics        logs
          ▼                        ▼               ▼              ▼
 +-------------------+  +---------------------+  +-------------------+
 | dataobs-poc-raw   |  | elastic-agent :8200  |  | Elasticsearch     |
 | dataobs-poc-      |  | (APM Server 9.x)     |  | :9200             |
 |   curated         |  +----------+----------+  | telemetry-metrics |
 | dataobs-poc-      |             │             | telemetry-logs    |
 |   quality         |             ▼             +-------------------+
 | dataobs-poc-      |  +---------------------+
 |   lineage         |  | Elasticsearch :9200  |
 +-------------------+  | traces-apm-*         |
                        | metrics-apm-*        |
                        | logs-apm-*           |
                        +----------+----------+
                                   │
                                   ▼
                        +---------------------+
                        |    Kibana :5601      |
                        | Observability / APM  |
                        | Custom dashboards    |
                        +---------------------+
```

### Why no separate `apm-server` container?

In **Elastic Stack 9.x**, APM Server is no longer a standalone Docker image. It runs as an integrated process inside **Elastic Agent**, managed by **Fleet Server**. The APM intake endpoint (`http://elastic-agent:8200`) accepts both the native Elastic APM protocol and **OTLP over gRPC/HTTP** natively. Traces sent by the OTel Collector land in `traces-apm-*` data streams and appear in **Kibana → Observability → APM → Services** automatically.

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Docker | 24+ |
| Docker Compose v2 | `docker compose` (not `docker-compose`) |

No Python, Java, or Spark installation needed — everything runs inside Docker.

> **Memory:** Allocate at least **6 GB RAM** to Docker Desktop for the full stack.

---

## Step 1 — Copy the env file

```bash
cp .env.poc .env.poc.local
```

The defaults work out of the box. Only edit `.env.poc.local` if you want custom passwords.

> ⚠️ `.env.poc.local` is gitignored. Never commit it.

---

## Step 2 — Start the infrastructure

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  up -d elasticsearch kibana fleet-server elastic-agent otel-collector
```

Services start in this order (healthchecks enforce it automatically):

```
elasticsearch
    └─► es-setup (one-shot: sets passwords + Fleet token)
            ├─► kibana
            └─► fleet-server
                    └─► elastic-agent  (APM Server on :8200)
                            └─► otel-collector
```

Wait until all services show **healthy** (~60–90 s on first pull):

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local ps
```

---

## Step 3 — Run the pipeline

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  run --rm pipeline
```

The pipeline runs once and exits. It will:

1. **Discover** 3 public datasets from data.gov.uk via CKAN API
2. **Download** each CSV/JSON file
3. **Parse & transform** with PySpark (`local[*]`)
4. **Quality-check** each dataset (null %, duplicates, row count, schema)
5. **Index** raw, curated, quality, and lineage docs into Elasticsearch
6. **Emit OTel traces** → OTel Collector → Elastic Agent APM (Kibana APM UI)
7. **Emit OTel metrics/logs** → OTel Collector → Elasticsearch directly
8. **Bootstrap** Kibana data views and 3 pre-built dashboards

Typical run time: **3–6 minutes**.

---

## Step 4 — Open Kibana

Navigate to **[http://localhost:5601](http://localhost:5601)**

- **Username:** `elastic`
- **Password:** value of `ELASTIC_PASSWORD` in `.env.poc.local` (default: `dataobs_poc_secret`)

### Where to look

#### Observability → APM → Services
The `dataobs-poc-pipeline` service appears here with:
- Full **distributed traces** for each pipeline stage
- **Stage duration** histograms and latency percentiles
- **Error tracking** for any failed stages
- **Trace waterfall** showing the full span breakdown

#### Analytics → Dashboards

| Dashboard | What you'll see |
|---|---|
| **[DataObs POC] Pipeline Health** | Stage durations, records ingested, OTel metrics |
| **[DataObs POC] Data Quality Overview** | Null %, duplicate ratio, row counts, pass/warn/fail |
| **[DataObs POC] Public Dataset Explorer** | Ingested transport, environment, govt data |

#### Discover — data views created automatically

| Data view | Content |
|---|---|
| `dataobs-poc-curated*` | Spark-processed records |
| `dataobs-poc-quality*` | Quality check results |
| `dataobs-poc-lineage*` | Lineage events |
| `dataobs-poc-telemetry-metrics*` | OTel pipeline metrics |
| `dataobs-poc-telemetry-logs*` | Pipeline structured logs |
| `traces-apm*` | APM distributed traces |
| `metrics-apm*` | APM service metrics |
| `logs-apm*` | APM log correlation |

---

## Tear down

```bash
# Stop containers and remove all volumes
docker compose -f docker-compose.poc.yml --env-file .env.poc.local down -v
```

---

## Configuration reference

All POC settings live in **`config/dataobs_poc.yaml`**.

### Pin specific datasets (skip CKAN auto-discovery)

```yaml
poc:
  data_sources:
    - name: my-dataset
      source_type: custom
      resource_url: "https://example.com/data.csv"
      format: csv
```

### Adjust quality thresholds

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

> Set Docker Desktop memory to at least **6 GB** in Preferences → Resources.
