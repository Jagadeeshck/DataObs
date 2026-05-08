# DataObs POC — Setup & Run Guide

> **Elastic Stack:** 9.4.0 (latest stable, April 2026)
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

## Step 1 — Use the committed env file

The repo ships `.env.poc` with safe POC defaults — every command in this
guide uses it directly:

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc up -d
```

If you want custom passwords or cloud endpoints, copy it to a local
override (gitignored) **and pass that file instead**:

```bash
cp .env.poc .env.poc.local           # gitignored, never committed
# edit .env.poc.local, then run:
docker compose -f docker-compose.poc.yml --env-file .env.poc.local up -d
```

> ⚠️ `.env.poc.local` is **optional** and gitignored. If you keep one
> around from an older checkout, make sure its values match the current
> `.env.poc` template (e.g. `OTEL_EXPORTER_OTLP_ENDPOINT`,
> `CADVISOR_PORT`, `OTEL_SERVICE_NAME`). Stale local overrides are the
> single most common cause of broken POC runs — when in doubt, delete
> `.env.poc.local` and start from `.env.poc`.

---

## Step 2 — Start the infrastructure

The POC boots a **single-node Elasticsearch** instance (`es01`) running ES
9.4.0 with `discovery.type=single-node`. Single-node mode skips the cluster
bootstrap check that — on ES 9.x with security enabled — would otherwise
require transport TLS / certificate setup, which is overkill for a local
POC. Pipeline, Kibana and Fleet all write to this one node.

> **Production / AWS reference architecture:** multi-node ES (3 master-
> eligible nodes) is the recommended topology, but it requires
> `xpack.security.transport.ssl.enabled=true` plus a CA + per-node certs.
> Use the Helm chart in `helm/` or your AWS OpenSearch domain instead of
> scaling this compose file out for production.

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc \
  up -d es01 kibana fleet-server elastic-agent otel-collector
```

Services start in this order (healthchecks enforce it automatically):

```
es01                         (single-node ES, discovery.type=single-node)
    └─► es-setup             (one-shot: passwords, ILM, index templates)
            ├─► kibana
            └─► fleet-server
                    └─► elastic-agent  (APM + Fleet OTel agent)
                            └─► otel-collector
```

> **Upgrade gotcha:** if you previously ran the POC on Elastic 8.x, 9.3
> or the multi-node 9.4 variant, the old `es*_data` Docker volumes are
> incompatible. Wipe them with
> `docker compose -f docker-compose.poc.yml down -v` before starting.

Wait until all services show **healthy** (~60–90 s on first pull):

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc ps
```

---

## Step 3 — Run the pipeline

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc \
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

## Step 3a — Verify indices, schemas & doc counts

```bash
ELASTIC_PASSWORD=dataobs_poc_elastic ./scripts/verify_poc.sh
```

The script prints cluster health, lists nodes, and walks every POC index
(`dataobs-test-data`, `dataobs-spark-results`, `dataobs-assets`,
`dataobs-quality`, `dataobs-freshness`, `dataobs-volume`, `dataobs-schema`,
`dataobs-lineage`, `dataobs-alerts`) showing doc counts and mapped fields.

Equivalent manual check in Kibana → Dev Tools:

```
GET _cat/indices/dataobs-*?v
GET dataobs-quality/_search
GET dataobs-spark-results/_mapping
```

## Step 4 — Open Kibana

Navigate to **[http://localhost:5601](http://localhost:5601)**

- **Username:** `elastic`
- **Password:** value of `ELASTIC_PASSWORD` in `.env.poc` (default: `dataobs_poc_elastic`)

### Where to look

#### Observability → APM → Services
The `dataobs-poc-pipeline` service appears here with:
- Full **distributed traces** for each pipeline stage
- **Stage duration** histograms and latency percentiles
- **Error tracking** for any failed stages
- **Trace waterfall** showing the full span breakdown

#### Analytics → Dashboards

### Analytics → Dashboards

| Dashboard | What you’ll see |
|---|---|
| **[DataObs POC] Pipeline Health** | Stage durations, records ingested, OTel metrics |
| **[DataObs POC] Data Quality Overview** | Null %, duplicate ratio, row counts, pass/warn/fail |
| **[DataObs POC] Public Dataset Explorer** | Browse road safety, air quality, local authority data |

### Discover

| Data view | Index / data stream |
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
docker compose -f docker-compose.poc.yml --env-file .env.poc down -v
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

Create `.env.poc.local` with the override (gitignored):
```bash
cp .env.poc .env.poc.local
# then edit .env.poc.local:
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
| Elasticsearch 9.4.0 | 1.5 GB |
| Kibana 9.4.0 | 1 GB |
| Fleet Server | 256 MB |
| Elastic Agent (APM) | 512 MB |
| OTel Collector | 256 MB |
| Pipeline (PySpark) | 1 GB |
| **Total** | **~4.5–6 GB** |

> Set Docker Desktop memory to at least **6 GB** in Preferences → Resources.
