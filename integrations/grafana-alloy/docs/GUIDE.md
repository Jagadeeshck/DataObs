# OpenTelemetry + Grafana Alloy → Grafana Cloud
## Step-by-step configuration guide

This guide walks through the complete pipeline:

```
Python Flask App
  └─▶ OTLP gRPC (port 4317)
        └─▶ Grafana Alloy (collector + pipeline)
              ├─▶ Resource detection + attribute enrichment
              ├─▶ Batch processor
              └─▶ Grafana Cloud OTLP endpoint
                    ├─▶ Tempo   (traces + service map)
                    ├─▶ Loki    (logs)
                    └─▶ Mimir   (metrics)
                          └─▶ Grafana Dashboards
                                ├─▶ Service Map
                                ├─▶ Anomaly detection (Grafana Application Observability)
                                └─▶ Drilldown: trace ↔ logs ↔ metrics
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker | 24+ | |
| Docker Compose | 2.20+ | |
| Python | 3.11+ | only needed for local dev without Docker |
| Grafana Cloud account | Free tier works | [sign up](https://grafana.com/auth/sign-up/create-user) |

---

## Step 1 — Obtain Grafana Cloud credentials

1. Log in to [grafana.com](https://grafana.com) → **My Account → Grafana Cloud stack**.
2. Navigate to **OpenTelemetry → Configure**. Note:
   - **OTLP Endpoint** — e.g. `https://otlp-gateway-prod-eu-west-0.grafana.net/otlp`
   - **Instance ID** — numeric, e.g. `123456`
3. Navigate to **Security → Service accounts → Add service account token**.
   Create a token with the following scopes:
   - `metrics:write`
   - `logs:write`
   - `traces:write`
4. Copy the token — it is shown only once.

> **Tip for EU users:** your OTLP gateway will contain `eu-west`. For US-east it will be `us-east`. Always use the gateway URL shown on the Configure page, not a hardcoded URL.

---

## Step 2 — Clone and configure

```bash
# Clone / copy the project
git clone <your-repo> otel-grafana-cloud
cd otel-grafana-cloud

# Copy and edit the env file — never commit the real .env
cp .env.example .env
```

Edit `.env`:

```dotenv
GRAFANA_CLOUD_OTLP_ENDPOINT=https://otlp-gateway-prod-eu-west-0.grafana.net/otlp
GRAFANA_CLOUD_INSTANCE_ID=123456
GRAFANA_CLOUD_API_KEY=glc_eyJxxxx==
OTEL_SERVICE_NAME=sample-python-app
DEPLOYMENT_ENVIRONMENT=development
```

---

## Step 3 — Understand the Grafana Alloy config

`alloy/config.alloy` uses Alloy's **River** (now called Alloy syntax) component model.
Each block represents a component that wires into the next via its `output` / `.input` references.

### Component pipeline

```
otelcol.receiver.otlp "default"
    → otelcol.processor.resourcedetection "default"
    → otelcol.processor.transform "cleanup"
    → otelcol.processor.transform "promote_env"   (metrics only)
    → otelcol.processor.batch "default"
    → otelcol.exporter.otlphttp "grafana_cloud"
```

### Key components explained

#### `otelcol.receiver.otlp "default"`
Listens on:
- `0.0.0.0:4317` — gRPC (used by the Python app)
- `0.0.0.0:4318` — HTTP/protobuf (for browser SDKs or direct SDK sends)

#### `otelcol.processor.resourcedetection "default"`
Auto-populates resource attributes from the host environment:
- `host.name` from OS hostname
- `os.type`, `os.description`
- Reads `OTEL_RESOURCE_ATTRIBUTES` env var for anything custom

#### `otelcol.processor.transform "cleanup"`
Removes verbose process attributes (`process.pid`, `process.command_args`, etc.) that inflate cardinality in Loki/Mimir.

#### `otelcol.processor.transform "promote_env"`
Copies `deployment.environment` and `service.version` from the resource down to each metric datapoint so they become Prometheus labels — enabling dashboard filtering by environment.

#### `otelcol.processor.batch "default"`
Buffers telemetry before sending:
- `send_batch_size = 512` — flush after 512 records
- `timeout = "5s"` — flush every 5 seconds regardless of batch size

This reduces API call volume significantly.

#### `otelcol.exporter.otlphttp "grafana_cloud"`
Sends all three signals to the single Grafana Cloud OTLP gateway. Grafana Cloud routes internally to Tempo/Loki/Mimir based on content type.

Configured with exponential retry (`5s → 30s`) and a local queue of 1000 items to absorb burst traffic without data loss.

#### `otelcol.auth.basic "grafana_cloud"`
Injects HTTP Basic auth headers using the instance ID as username and API key as password.

---

## Step 4 — Understand the Python app instrumentation

`app/app.py` initialises three separate providers before Flask starts:

### Traces
```python
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True))
)
trace.set_tracer_provider(tracer_provider)
```
`FlaskInstrumentor().instrument_app(app)` then automatically creates spans for every HTTP request — no manual code needed per route.

### Metrics
```python
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
```
Custom instruments (`Counter`, `Histogram`, `UpDownCounter`) are created once at startup and reused across requests.

### Logs — OTLP bridge
```python
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTLP_ENDPOINT, insecure=True))
)
set_logger_provider(logger_provider)
otel_handler = LoggingHandler(logger_provider=logger_provider)
logging.getLogger().addHandler(otel_handler)
LoggingInstrumentor().instrument(set_logging_format=True)
```
`LoggingInstrumentor` injects `trace_id` and `span_id` into every `logging.*` call, enabling **log-to-trace drilldown** in Grafana.

### Shared Resource
All three providers share the same `Resource` object, so every signal carries identical `service.name`, `service.version`, `deployment.environment` — the foundation of correlated observability.

### Checkout span hierarchy (ideal for trace drilldown)
```
checkout                       ← root span
├── validate-order             ← child span
├── check-inventory            ← child span
└── process-payment            ← child span
    └── payment_authorized     ← span event
```
Each child span adds attributes (`payment.total_usd`, `inventory.available`) visible in Tempo's drilldown view.

---

## Step 5 — Start the stack

```bash
docker compose --env-file .env up --build
```

Expected startup order:
1. `grafana-alloy` starts and loads `config.alloy`
2. `alloy` health check passes (`/-/ready`)
3. `sample-python-app` starts and begins exporting telemetry
4. `load-generator` fires HTTP traffic every 3 seconds

### Verify Alloy is healthy

```bash
# Alloy UI — shows component graph and live pipeline status
open http://localhost:12345

# Alloy readiness check
curl http://localhost:12345/-/ready
# → "Alloy is ready."
```

### Verify the app is running

```bash
curl http://localhost:5000/health
# → {"service":"sample-python-app","status":"healthy"}

# Trigger a checkout manually
curl -X POST http://localhost:5000/checkout \
  -H "Content-Type: application/json" \
  -d '{"product_id":"P001","quantity":2}'

# Trigger a deliberate error (for anomaly detection testing)
curl http://localhost:5000/simulate-error
```

---

## Step 6 — Verify data in Grafana Cloud

Allow ~60–90 seconds for the first batch to arrive.

### Traces in Tempo

1. Grafana Cloud UI → **Explore** → datasource: **Tempo**
2. Search by `service.name = sample-python-app`
3. Click any trace → expand the **checkout** span tree
4. Click a span → use **Logs for this span** to jump to correlated Loki logs

### Logs in Loki

```logql
{service_name="sample-python-app"}
```

Add trace correlation:

```logql
{service_name="sample-python-app"} | json | trace_id != ""
```

Click the `trace_id` value in any log line → opens the linked trace in Tempo.

### Metrics in Prometheus / Mimir

```promql
# Request rate
sum(rate(http_server_requests_total{service_name="sample-python-app"}[5m]))

# p99 latency
histogram_quantile(0.99,
  sum by (le) (rate(http_server_request_duration_seconds_bucket{service_name="sample-python-app"}[5m]))
)

# Error rate
sum(rate(http_server_requests_total{service_name="sample-python-app",http_status_code=~"5.."}[5m]))
/ sum(rate(http_server_requests_total{service_name="sample-python-app"}[5m]))

# Order revenue rate (USD/min)
sum(rate(business_order_value_USD_sum{service_name="sample-python-app"}[5m])) * 60
```

---

## Step 7 — Import the dashboard

1. In Grafana Cloud → **Dashboards → Import**
2. Upload `grafana/provisioning/dashboards/sample-app-dashboard.json`
3. Select your Prometheus and Loki datasources when prompted
4. Click **Import**

The dashboard includes:
- **Stat panels**: request rate, error rate, p99 latency, active requests
- **Time series**: request rate by route, latency percentiles (p50/p95/p99)
- **Business panel**: order revenue rate + error rate by HTTP status code
- **Logs panel**: live Loki stream with trace correlation enabled

---

## Step 8 — Set up Service Map

The service map requires Grafana Application Observability:

1. Grafana Cloud → **Application** (or Grafana Application Observability tile)
2. It automatically reads your Tempo trace data and builds the service dependency graph from span relationships
3. Click any service node → drilldown to:
   - RED metrics for that service (Rate / Error / Duration)
   - Linked traces
   - Correlated logs

**How it works**: Tempo parses `spanKind`, `peer.service`, and parent-child span relationships to build the service graph. Alloy's `otelcol.connector.host_info` component (optional, shown in comments in the config) can enhance this further for infrastructure-level host graphs.

---

## Step 9 — Anomaly detection

Grafana Application Observability includes built-in anomaly detection for:
- **Error rate spikes** — detected via ML baseline on the error rate time series
- **Latency regressions** — p95/p99 deviations from rolling baseline
- **Throughput drops** — sudden drops in request rate

To surface these:
1. Go to **Application** → select `sample-python-app`
2. View the **Insights** tab — anomalies are highlighted inline with the time series
3. Each anomaly links to traces from the anomalous window

You can also set up **Grafana Alerting** rules using these PromQL expressions:

```yaml
# High error rate alert
- alert: HighErrorRate
  expr: |
    sum(rate(http_server_requests_total{service_name="sample-python-app",http_status_code=~"5.."}[5m]))
    / sum(rate(http_server_requests_total{service_name="sample-python-app"}[5m]))
    > 0.05
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Error rate > 5% on sample-python-app"

# p99 latency alert
- alert: HighLatency
  expr: |
    histogram_quantile(0.99, sum by (le) (
      rate(http_server_request_duration_seconds_bucket{service_name="sample-python-app"}[5m])
    )) > 1.0
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "p99 latency > 1s on sample-python-app"
```

---

## Step 10 — Drilldown correlation workflows

### Trace → Logs
1. Open any trace in Tempo
2. Select a span → click **Logs for this span**
3. Loki is queried automatically using `trace_id` and `span_id` from the span

### Log → Trace
1. In Loki Explore, click the `trace_id` value in any log record
2. The derived field link opens the corresponding trace in Tempo

### Metric → Trace (exemplars)
Prometheus/Mimir stores trace exemplars alongside metric samples:
- In any time series panel → hover a data point → click the diamond (◆) exemplar
- Opens the specific trace that produced that metric observation

Enable exemplars in your Prometheus datasource config:
```yaml
jsonData:
  exemplarTraceIdDestinations:
    - name: traceID
      datasourceUid: tempo-grafana-cloud
```

---

## Project structure

```
otel-grafana-cloud/
├── app/
│   ├── app.py                  # Flask app — traces, metrics, logs via OTLP
│   ├── requirements.txt        # OTel SDK + Flask dependencies
│   └── Dockerfile              # Python 3.12 slim container
├── alloy/
│   └── config.alloy            # Grafana Alloy pipeline config
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasources.yaml    # Tempo + Loki + Prometheus config
│       └── dashboards/
│           └── sample-app-dashboard.json
├── docs/
│   └── GUIDE.md                # This file
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## Troubleshooting

### No data appearing in Grafana Cloud

1. Check Alloy logs:
   ```bash
   docker compose logs alloy --follow
   ```
   Look for `export failed` or `authentication` errors.

2. Verify credentials:
   ```bash
   # Test OTLP endpoint directly
   curl -u "$GRAFANA_CLOUD_INSTANCE_ID:$GRAFANA_CLOUD_API_KEY" \
     "$GRAFANA_CLOUD_OTLP_ENDPOINT/v1/metrics" \
     -H "Content-Type: application/x-protobuf" \
     --data-binary "" -v
   # Expect: 400 Bad Request (not 401) — means auth works
   ```

3. Check the Alloy UI at `http://localhost:12345` → component graph should show green for all components.

### `insecure=True` error on OTLP exporter

In `app.py`, the exporter targets `http://alloy:4317` (plain gRPC, no TLS). The `insecure=True` flag is correct for container-internal communication. Never set this for production external endpoints.

### Traces appear but no service map

The service map requires at least **two spans with a parent-child relationship** to show edges. Run a few checkout requests — the `checkout → validate-order → check-inventory → process-payment` hierarchy satisfies this immediately.

### Logs not correlated to traces

Ensure `LoggingInstrumentor().instrument(set_logging_format=True)` runs **before** any logger is created. If you create a module-level logger before calling this, it won't inherit the trace-context formatter.

---

## Extending to Kubernetes

Replace the Docker Compose `alloy` service with a Helm-deployed Alloy DaemonSet:

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm install alloy grafana/alloy \
  --namespace monitoring --create-namespace \
  --set alloy.configMap.create=true \
  --set-file alloy.configMap.content=alloy/config.alloy \
  --set env[0].name=GRAFANA_CLOUD_OTLP_ENDPOINT \
  --set env[0].value="$GRAFANA_CLOUD_OTLP_ENDPOINT" \
  --set env[1].name=GRAFANA_CLOUD_INSTANCE_ID \
  --set env[1].value="$GRAFANA_CLOUD_INSTANCE_ID" \
  --set env[2].name=GRAFANA_CLOUD_API_KEY \
  --set env[2].value="$GRAFANA_CLOUD_API_KEY"
```

Point your Python app's `OTEL_EXPORTER_OTLP_ENDPOINT` to:
```
http://alloy.monitoring.svc.cluster.local:4317
```

Add `discovery.kubernetes` blocks to Alloy's config to auto-discover pods and enrich spans with K8s metadata (`k8s.namespace.name`, `k8s.pod.name`, `k8s.node.name`).
