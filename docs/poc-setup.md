# DataObs POC — Setup & Run Guide

This guide covers how to stand up the DataObs Proof-of-Concept pipeline locally
in under 10 minutes.  The POC demonstrates all four observability towers
(Full Stack, Pipeline, Data, Business) using real public open data from
[data.gov.uk](https://www.data.gov.uk) and a local Spark + Elasticsearch + Kibana stack.

---

## Architecture

```
 data.gov.uk (CKAN API)
       │
       │  HTTP download
       ▼
  Local Spark Job  ──► OTel Collector ──► Elasticsearch
       │                                        │
       │  bulk index                            │
       ▼                                        ▼
  dataobs-poc-raw          ◄─────────── Kibana Dashboards
  dataobs-poc-curated
  dataobs-poc-quality
  dataobs-poc-lineage
```

---

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Java 11+ (for PySpark)

### 2. Start the stack

```bash
docker compose up -d elasticsearch kibana otel-collector
```

Wait for Elasticsearch (`http://localhost:9200`) and Kibana (`http://localhost:5601`) to be healthy.

### 3. Configure POC mode

```bash
cp config/dataobs.example.yaml config/dataobs.yaml
```

Edit `config/dataobs.yaml` and set:

```yaml
poc:
  enabled: true
```

All other POC settings have sensible defaults.  Elasticsearch and Kibana
credentials are read from environment variables (`ELASTICSEARCH_URL`,
`ELASTICSEARCH_USER`, `ELASTICSEARCH_PASSWORD`, `KIBANA_URL`) or fall
back to `http://localhost:9200` / `http://localhost:5601`.

### 4. Install Python dependencies

```bash
pip install -r requirements-poc.txt
```

### 5. Run the pipeline

```bash
chmod +x scripts/run_poc_pipeline.sh
./scripts/run_poc_pipeline.sh
```

This will:
1. Auto-discover 3 public datasets from data.gov.uk (road safety, air quality, local authority)
2. Download and parse each file locally
3. Run Spark transformations (normalise columns, add metadata)
4. Execute baseline quality checks per dataset
5. Index everything into Elasticsearch
6. Import Kibana index patterns and dashboards

---

## Custom Data Sources

To use your own datasets instead of the auto-discovered defaults, add them
to `poc.data_sources` in `config/dataobs.yaml`:

```yaml
poc:
  enabled: true
  data_sources:
    - name: my-dataset
      source_type: custom
      resource_url: "https://example.com/data.csv"
      format: csv
```

When `data_sources` is non-empty the CKAN auto-discovery is skipped entirely.

---

## Kibana Dashboards

After a successful pipeline run, open Kibana at `http://localhost:5601`.
Three dashboards are created automatically:

| Dashboard | Description |
|---|---|
| **[DataObs POC] Pipeline Health** | Stage durations, records ingested, pipeline pass/fail |
| **[DataObs POC] Data Quality Overview** | Null %, duplicate ratio, row counts per dataset |
| **[DataObs POC] Public Dataset Explorer** | Browse the ingested road safety, air quality, and LA profile data |

You can extend any dashboard by adding Lens visualisations on top of the
`dataobs-poc-curated*` or `dataobs-poc-quality*` index patterns.

---

## Telemetry

The pipeline emits OTel traces and metrics to the configured OTel Collector
endpoint (default: `http://otel-collector:4318`).  If the OTel SDK is not
installed or the endpoint is unreachable the pipeline falls back to
structured logger output — it never crashes due to missing telemetry.

Telemetry is forwarded to Elasticsearch via the OTel Collector and is
visible in the **[DataObs POC] Pipeline Health** dashboard.

---

## Elasticsearch Indices

| Index | Content |
|---|---|
| `dataobs-poc-raw` | Raw parsed records from source files |
| `dataobs-poc-curated` | Spark-normalised records |
| `dataobs-poc-quality` | Quality check results per check per dataset |
| `dataobs-poc-lineage` | Lineage events (source → raw → curated) |

---

## Extending the POC

- **Add a new dataset**: add an entry to `poc.data_sources` or extend `DEFAULT_QUERIES` in `src/poc/datasets.py`
- **Add a quality check**: extend `run_basic_quality_checks()` in `src/poc/quality.py`
- **Add a Kibana visualisation**: edit `kibana/dataobs-poc-saved-objects.ndjson`
- **Connect to AWS**: set `poc.elasticsearch.host` to your AWS OpenSearch endpoint and configure IAM credentials
