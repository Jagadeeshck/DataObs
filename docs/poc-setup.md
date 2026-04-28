# DataObs POC — Setup & Run Guide

This guide gets the DataObs Proof-of-Concept running **end-to-end in under 10 minutes** using three dedicated files:

| File | Purpose |
|---|---|
| `.env.poc` | All environment variables for the POC stack |
| `config/dataobs_poc.yaml` | Full POC pipeline configuration |
| `docker-compose.poc.yml` | Self-contained Docker stack (ES + Kibana + OTel + pipeline) |

No changes to the main `docker-compose.yml` or `config/dataobs.yaml` are required.

---

## Architecture

```
 data.gov.uk (CKAN API)
       │  auto-discovered CSV/JSON datasets
       ▼
 ┌─────────────────────┐     OTLP/HTTP      ┌──────────────────────┐
 │  pipeline container │ ─────────────────► │  otel-collector:4318 │
 │  (PySpark + Python) │                    └──────────┬───────────┘
 └─────────┬───────────┘                               │ ES exporter
           │ bulk index                                ▼
           ▼                                ┌──────────────────────┐
 ┌─────────────────────┐                    │    Elasticsearch     │
 │ dataobs-poc-raw     │ ◄──────────────────│   :9200  (single-    │
 │ dataobs-poc-curated │                    │    node, security)   │
 │ dataobs-poc-quality │                    └──────────┬───────────┘
 │ dataobs-poc-lineage │                               │
 └─────────────────────┘                               ▼
                                            ┌──────────────────────┐
                                            │  Kibana  :5601       │
                                            │  3 pre-built         │
                                            │  dashboards          │
                                            └──────────────────────┘
```

---

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (`docker compose`) | bundled with Docker Desktop |

No Python, Java, or Spark installation is needed on your machine — everything runs inside Docker.

---

## Step-by-step

### 1 — Copy the env file

```bash
cp .env.poc .env.poc.local
```

The defaults in `.env.poc` work out of the box for a local POC.
If you want non-default passwords, edit `.env.poc.local` now:

```bash
# only if you want to change passwords
nano .env.poc.local
```

> ⚠️  `.env.poc.local` is gitignored. Never commit it.

### 2 — Start the stack

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  up -d elasticsearch kibana otel-collector
```

This starts Elasticsearch, runs the one-shot `es-setup` init container
(sets the `kibana_system` password automatically), then starts Kibana
and the OTel Collector.

Wait until all three are healthy (~30–60 s):

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local ps
# All three should show   Status: healthy
```

### 3 — Run the pipeline

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  run --rm pipeline
```

The pipeline container will:
1. **Discover** up to 3 public datasets from data.gov.uk (transport, environment, government)
2. **Download** each CSV/JSON file
3. **Parse & transform** with PySpark
4. **Quality-check** each dataset (row count, null %, duplicates)
5. **Index** raw, curated, quality, and lineage documents into Elasticsearch
6. **Emit** OTel traces and metrics to the collector
7. **Bootstrap** Kibana data views and 3 dashboards

Typical run time: **2–5 minutes** (depending on download speed).

### 4 — Open Kibana

Navigate to [http://localhost:5601](http://localhost:5601)

- **Username:** `elastic`
- **Password:** value of `ELASTIC_PASSWORD` in your `.env.poc.local` (default: `dataobs_poc_secret`)

Three dashboards are available under **Analytics → Dashboards**:

| Dashboard | What you'll see |
|---|---|
| **[DataObs POC] Pipeline Health** | Stage durations, records ingested per dataset, OTel spans |
| **[DataObs POC] Data Quality Overview** | Null %, duplicate ratio, row counts, pass/warn/fail per check |
| **[DataObs POC] Public Dataset Explorer** | Browse the ingested road safety, air quality, and LA profile data |

---

## Tearing down

```bash
# Stop and remove containers + volumes
docker compose -f docker-compose.poc.yml --env-file .env.poc.local down -v
```

---

## Configuration reference

All POC settings live in **`config/dataobs_poc.yaml`** — no need to touch `config/dataobs.yaml`.

### Pin specific datasets (skip auto-discovery)

Uncomment and fill in `poc.data_sources` in `config/dataobs_poc.yaml`:

```yaml
poc:
  data_sources:
    - name: my-dataset
      source_type: custom
      resource_url: "https://example.com/data.csv"
      format: csv
```

When `data_sources` is non-empty, CKAN auto-discovery is skipped entirely.

### Change quality thresholds

```yaml
poc:
  processing:
    quality_rules:
      max_null_pct_warn: 10.0   # warn above 10 % nulls
      max_null_pct_fail: 30.0   # fail above 30 % nulls
      duplicate_threshold_pct: 2.0
```

### Point at AWS OpenSearch instead of local ES

Update `.env.poc.local`:

```bash
ELASTICHOST=https://your-opensearch-domain.eu-west-1.es.amazonaws.com
ELASTIC_PASSWORD=your-master-password
```

Then skip the local elasticsearch and es-setup services:

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  up -d kibana otel-collector
docker compose -f docker-compose.poc.yml --env-file .env.poc.local \
  run --rm pipeline
```

---

## Elasticsearch indices created

| Index | Content |
|---|---|
| `dataobs-poc-raw` | Raw parsed records from source files |
| `dataobs-poc-curated` | Spark-normalised records with metadata |
| `dataobs-poc-quality` | Quality check results (one doc per check per dataset) |
| `dataobs-poc-lineage` | Lineage events (source URL → raw → curated) |
| `dataobs-poc-telemetry-traces` | OTel traces from the pipeline stages |
| `dataobs-poc-telemetry-metrics` | OTel metrics (stage duration, records ingested) |
| `dataobs-poc-telemetry-logs` | OTel log records |
