# POC Observability Architecture — Elastic Agent + OTel

## Overview

The DataObs POC uses a **dual telemetry path** to maximise observability coverage:

```
┌──────────────────────────────────────────────────────────────┐
│                     Signal Sources                           │
│  Pipeline (Python/Spark)  │  Docker Containers  │  Host OS   │
└────────┬──────────────────┴──────────┬──────────┴────────────┘
         │ OTLP HTTP (port 4318)       │ Docker API / filelog
         ▼                             ▼
┌─────────────────────┐   ┌────────────────────────────────────┐
│  OTel Collector     │   │  Elastic Agent (Fleet-managed)     │
│  (contrib:0.99.0)   │   │  Integrations:                     │
│                     │   │  - APM Server (port 8200)          │
│  Receivers:         │   │  - Docker integration (metrics)    │
│  - otlp (pipeline)  │   │  - System integration (host)       │
│  - hostmetrics      │   │  - Log collection                  │
│  - docker_stats     │   └──────────────┬─────────────────────┘
│  - prometheus/cadv  │                  │
│  - filelog          │                  │ Enrolled via Fleet Server
└──────┬──────────────┘                  │
       │                                 │
       │ Dual export                     │
       ├──────────────────────────────────
       │
       ├──► APM Server (elastic-agent:8200)  → Kibana APM UI
       │
       └──► Elasticsearch (elasticsearch:9200)
               └──► dataobs-otel-traces
               └──► dataobs-otel-metrics
               └──► dataobs-otel-logs
               └──► dataobs-otel-container-logs
                    ↕ Kibana Discover / Dashboards
```

## What Gets Monitored

| Signal | Source | Destination | Kibana View |
|--------|--------|-------------|-------------|
| Pipeline traces (Python/Spark) | OTel SDK → OTel Collector | ES `dataobs-otel-traces` + APM | APM UI + Discover |
| Pipeline metrics | OTel SDK → OTel Collector | ES `dataobs-otel-metrics` + APM | Discover + Dashboards |
| Pipeline logs | OTel SDK → OTel Collector | ES `dataobs-otel-logs` + APM | Discover |
| Host CPU/mem/disk/net | OTel hostmetrics | ES `dataobs-otel-metrics` + APM | Discover |
| Docker container metrics (OTel) | OTel docker_stats | ES `dataobs-otel-metrics` + APM | Discover |
| Docker container metrics (cAdvisor) | Prometheus scrape | ES `dataobs-otel-metrics` + APM | Discover |
| Docker container metrics (Fleet) | Elastic Agent Docker integration | `.ds-metrics-docker.*` | Infrastructure → Containers |
| Docker container logs (filelog) | OTel filelog receiver | ES `dataobs-otel-container-logs` + APM | Discover |
| Docker container logs (Fleet) | Elastic Agent Docker integration | `.ds-logs-docker.*` | Logs |
| Host system metrics (Fleet) | Elastic Agent System integration | `.ds-metrics-system.*` | Infrastructure |
| APM transactions/errors | elastic-agent APM Server | `.ds-traces-apm.*` | APM UI |

## Root Cause Fixes Applied

### Fix 1: OTel DNS Resolution (`NameResolutionError`)

**Symptom:** `Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)`

**Root Cause:** `docker compose run --rm pipeline` attaches the container to the **default Docker bridge network**, not to `dataobs-poc`. Service names (like `otel-collector`) are only resolvable within the custom named network.

**Fix:** Added explicit `networks: [dataobs-poc]` to the `pipeline` service in `docker-compose.poc.yml`.

### Fix 2: No Docker Metrics in Elastic

**Root Cause 1 (Elastic Agent):** The `elastic-agent` container had no Docker socket mount (`/var/run/docker.sock`), so the Docker integration installed via Fleet had no access to the Docker API.

**Fix:** Added volume mounts to `elastic-agent`:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
  - /var/lib/docker/containers:/var/lib/docker/containers:ro
  - /proc:/hostfs/proc:ro
  - /sys:/hostfs/sys:ro
```

**Root Cause 2 (OTel Collector):** Only cAdvisor (Prometheus scrape) was used for container metrics. The `docker_stats` receiver was not configured.

**Fix:** Added `docker_stats` receiver to `otel-collector-poc.yaml` and new `metrics/docker` pipeline.

### Fix 3: No Data Visible in Kibana Discover

**Root Cause:** All OTel data was being exported exclusively to APM Server via `otlp/apm` exporter. APM data only appears in the APM UI, not in Kibana Discover.

**Fix:** Added `elasticsearch` exporter in OTel collector config. All signals now export to **both** APM and Elasticsearch directly.

### Fix 4: Missing Docker + System Fleet Integrations

**Root Cause:** `kibana-setup` only configured APM and Fleet Server integrations. No System or Docker integrations were enrolled on the agent policy.

**Fix:** `kibana-setup` now installs and configures:
- `system` integration (CPU, memory, disk, network + syslog)
- `docker` integration (container metrics, container logs)

## Verification

After `docker compose -f docker-compose.poc.yml --env-file .env.poc up -d`:

```bash
# 1. Check all containers are healthy
docker compose -f docker-compose.poc.yml ps

# 2. Verify OTel collector is receiving and exporting
curl http://localhost:13133/       # health check
curl http://localhost:55679/debug/servicez  # zpages service list

# 3. Verify data in Elasticsearch
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cat/indices/dataobs-otel*
# Should show: dataobs-otel-traces, dataobs-otel-metrics, dataobs-otel-logs

# 4. Check Elastic Agent is enrolled and Docker integration is active
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/.ds-metrics-docker.*/_search?size=1

# 5. Run pipeline and confirm traces reach ES
docker compose -f docker-compose.poc.yml --env-file .env.poc run --rm pipeline
curl -u elastic:$ELASTIC_PASSWORD 'http://localhost:9200/dataobs-otel-traces/_count'
# Expected: count > 0
```

## APM Agent Setup (Python & Java)

For **Python** services, use the `elastic-apm` library:

```python
# requirements.txt
elastic-apm>=6.22.0

# In your Python service:
import elasticapm
elasticapm.instrument()
client = elasticapm.Client(
    service_name="my-python-service",
    server_url="http://localhost:8200",  # elastic-agent APM port
    secret_token=os.environ["APM_SECRET_TOKEN"],
    environment="poc",
)
```

For **Java** services (e.g. Spark executors), attach the Elastic APM Java agent:

```bash
# Download the agent jar
curl -L -o elastic-apm-agent.jar \
  https://repo1.maven.org/maven2/co/elastic/apm/elastic-apm-agent/1.51.0/elastic-apm-agent-1.51.0.jar

# Add to JVM opts (SPARK_SUBMIT_OPTS or spark-defaults.conf)
-javaagent:/path/to/elastic-apm-agent.jar
-Delastic.apm.service_name=spark-driver
-Delastic.apm.server_url=http://elastic-agent:8200
-Delastic.apm.secret_token=${APM_SECRET_TOKEN}
-Delastic.apm.environment=poc
```
