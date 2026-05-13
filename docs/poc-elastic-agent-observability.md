# POC Observability Architecture — Elastic Agent + Elastic APM

## Overview

The DataObs POC ships **all** telemetry through the Elastic Stack: the
Fleet-managed **Elastic Agent** collects host/container/system signals,
and the **Elastic APM Python agent** in the pipeline emits trace
transactions/spans plus custom metrics straight to the APM Server
hosted by the same Elastic Agent. The standalone OpenTelemetry
Collector is no longer part of the default path — it is gated behind
an optional `otel` Compose profile for users who want to experiment
with EDOT/OTLP ingestion.

```
┌──────────────────────────────────────────────────────────────┐
│                     Signal Sources                           │
│  Pipeline (Python/Spark)  │  Docker Containers  │  Host OS   │
└────────┬──────────────────┴──────────┬──────────┴────────────┘
         │ Elastic APM Python agent     │ Docker API / filelog
         │ (HTTP POST /intake/v2/events)│
         ▼                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Elastic Agent (Fleet-managed) — single container            │
│  ─────────────────────────────────────────────────────────── │
│  Integrations enrolled by kibana-setup:                      │
│    • APM Server         (port 8200) → traces / metrics       │
│    • Docker integration → .ds-metrics-docker.*               │
│                          → .ds-logs-docker.*                 │
│    • System integration → .ds-metrics-system.*               │
│                          → .ds-logs-system.*                 │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
        Elasticsearch (es01:9200)
        ├── traces-apm-*           ← APM transactions / spans
        ├── metrics-apm.*          ← APM custom metrics + agent metrics
        ├── logs-apm.error-*       ← APM captured exceptions
        ├── .ds-metrics-docker.*   ← Container metrics
        ├── .ds-logs-docker.*      ← Container logs
        ├── .ds-metrics-system.*   ← Host metrics
        ├── dataobs-poc-* / dataobs-test-data / dataobs-spark-results
        └── dataobs-{assets,quality,freshness,volume,schema,lineage,alerts}
                                   ↕ Kibana Discover / APM UI / Dashboards
```

## What Gets Monitored

| Signal | Source | Data stream / Index | Kibana View |
|---|---|---|---|
| Pipeline traces (Python) | `elastic-apm` Python agent | `traces-apm-*` | APM UI |
| Pipeline custom metrics | `elastic-apm` Python agent | `metrics-apm.*` | APM UI / Discover |
| Pipeline log correlation | `elastic-apm` log integration | linked via `trace.id` | APM UI |
| Spark stage spans | `SparkApmInstrumentation` | `traces-apm-*` | APM UI |
| Container metrics | Elastic Agent Docker integration | `.ds-metrics-docker.*` | Infrastructure → Containers |
| Container logs | Elastic Agent Docker integration | `.ds-logs-docker.*` | Logs |
| Host metrics | Elastic Agent System integration | `.ds-metrics-system.*` | Infrastructure |
| Host logs | Elastic Agent System integration | `.ds-logs-system.*` | Logs |
| Pipeline raw + curated rows | Direct ES bulk index | `dataobs-test-data`, `dataobs-spark-results` | Discover |
| Data observability docs | `ObservabilityWriter` | `dataobs-{assets,quality,freshness,volume,schema,lineage,alerts}` | Discover |


## ECS + OpenTelemetry schema contract

The selected POC path is Elastic-native: Elastic Agent/Fleet integrations
write host, container, Docker, system and APM data streams that already use
Elastic Common Schema (ECS). For the DataObs-specific documents written
directly to Elasticsearch (`dataobs-assets`, `dataobs-quality`,
`dataobs-freshness`, `dataobs-volume`, `dataobs-schema`, `dataobs-lineage`
and `dataobs-alerts`), `ObservabilityWriter` adds the same common envelope so
these records correlate cleanly with Elastic Agent-collected telemetry:

| Contract area | Fields populated | Purpose |
|---|---|---|
| ECS versioning | `ecs.version` | Marks records as ECS-shaped events. |
| Data streams | `data_stream.type`, `data_stream.dataset`, `data_stream.namespace`, `event.dataset` | Keeps custom records aligned with Elastic data stream naming conventions. |
| Event taxonomy | `event.kind`, `event.category`, `event.type`, `event.module`, `event.provider`, `event.action`, `event.outcome` | Makes checks, freshness, volume, schema, lineage and alert records queryable with standard ECS filters. |
| Service/resource identity | `service.name`, `service.namespace`, `service.type`, `deployment.environment.name` | Mirrors OpenTelemetry resource semantic conventions and Elastic APM service identity. |
| Telemetry provenance | `telemetry.sdk.language`, `telemetry.distro.name`, `observer.type` | Documents that pipeline signals come from Python/Elastic APM via the Elastic Agent-hosted APM Server. |
| Tenant labels | `labels.tenant` plus legacy `tenant` | Provides ECS-style filtering while preserving existing DataObs queries. |

Dataset names use dotted ECS-style values (`dataobs.assets`,
`dataobs.quality`, `dataobs.freshness`, `dataobs.volume`,
`dataobs.schema`, `dataobs.lineage`, `dataobs.alerts`). The legacy custom
fields remain in place for backwards compatibility, but new fields should use
ECS or OpenTelemetry semantic-convention names where an equivalent exists.

References: [Elastic ECS reference](https://www.elastic.co/docs/reference/ecs/),
[ECS data stream fields](https://www.elastic.co/docs/reference/ecs/ecs-data_stream),
and [OpenTelemetry resource semantic conventions](https://opentelemetry.io/docs/specs/semconv/resource/).

## Why we removed the standalone OTel Collector from the default path

Repeated local runs hit the same failure mode:

```
NameResolutionError(host='otel-collector', port=4318)
```

Root causes (each fixed in a previous PR, but the issue kept resurfacing):

1. `docker compose run --rm pipeline` attached to the default bridge
   network in some Docker Desktop versions, so `otel-collector` was
   not DNS-resolvable.
2. The `FROM scratch` collector image has no shell/curl/wget, so
   `service_healthy` could never gate the pipeline.
3. Stale `.env.poc.local` files re-introduced
   `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318` even when
   the compose file had been fixed.

The Fleet-managed Elastic Agent already runs APM Server, so routing
the pipeline directly at `http://elastic-agent:8200` collapses three
hop points (pipeline → otel-collector → elastic-agent → ES) into one
(`pipeline → elastic-agent → ES`). It also removes the `FROM scratch`
healthcheck quirk and a separate Docker socket mount.

## Default run

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc up -d
docker compose -f docker-compose.poc.yml --env-file .env.poc run --rm pipeline
```

The `pipeline` service depends on `elastic-agent`, sets
`ELASTIC_APM_SERVER_URL=http://elastic-agent:8200`, and exports
`OTEL_SDK_DISABLED=true` so the OTel SDK is never bootstrapped.

## Verification

```bash
# 1. Containers
docker compose -f docker-compose.poc.yml ps

# 2. APM Server is reachable inside the network
docker compose -f docker-compose.poc.yml exec elastic-agent \
  curl -sf http://localhost:8200/

# 3. APM data in Elasticsearch (traces + metrics)
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cat/indices/traces-apm*
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cat/indices/metrics-apm*

# 4. Pipeline + Spark transaction count
curl -u elastic:$ELASTIC_PASSWORD \
  'http://localhost:9200/traces-apm-*/_count?q=service.name:dataobs-poc-pipeline'

# 5. Container + system data streams
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cat/indices/.ds-metrics-docker*
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cat/indices/.ds-logs-docker*
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cat/indices/.ds-metrics-system*

# 6. DataObs observability docs
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cat/indices/dataobs-*
```

In Kibana:

* **APM → Services → `dataobs-poc-pipeline`** for transactions,
  span timings, and errors.
* **Observability → Logs / Infrastructure** for container + host
  signals.
* **Discover → `dataobs-quality` / `dataobs-lineage` / etc.** for the
  Soda/Monte-Carlo/Acceldata-style data observability docs.

## Optional: standalone OTel Collector (`--profile otel`)

The `otel-collector` service is retained behind the `otel` Compose
profile for EDOT experiments. To enable it:

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc \
  --profile otel up -d
```

When you also want the pipeline to send OTLP to that collector,
override two env vars on the `run` invocation:

```bash
docker compose -f docker-compose.poc.yml --env-file .env.poc \
  --profile otel run --rm \
  -e OTEL_SDK_DISABLED=false \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318 \
  pipeline
```

This mode is **not part of the default POC** and is documented for
completeness only.

## APM Agent Setup (reference)

The pipeline already wires this in `src/poc/apm.py`. For other Python
services in this repo, the same config applies:

```python
import elasticapm
elasticapm.instrument()
client = elasticapm.Client({
    "SERVICE_NAME": "my-python-service",
    "SERVER_URL": "http://elastic-agent:8200",  # default Docker URL
    "SECRET_TOKEN": os.environ["APM_SECRET_TOKEN"],
    "ENVIRONMENT": "poc",
    "GLOBAL_LABELS": "service.namespace=dataobs,deployment.environment.name=poc",
})
```

For Java services (e.g. Spark executors when running outside the
local POC), attach the Elastic APM Java agent:

```
-javaagent:/opt/elastic-apm-agent.jar
-Delastic.apm.service_name=spark-driver
-Delastic.apm.server_url=http://elastic-agent:8200
-Delastic.apm.secret_token=${APM_SECRET_TOKEN}
-Delastic.apm.environment=poc
```
