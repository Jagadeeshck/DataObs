# Grafana Alloy → Grafana Cloud Integration

This integration adds a **Grafana Alloy** (OTel Collector) pipeline to DataObs,
forwarding metrics, logs, and traces from a sample Python app to **Grafana Cloud**
(Tempo, Loki, Mimir) for service maps, anomaly detection, and drilldown correlation.

## Architecture

```
Sample Python App (Flask + OTel SDKs)
  └─▶ OTLP gRPC → Grafana Alloy (collector pipeline)
                      ├─ Resource detection
                      ├─ Attribute enrichment / cleanup
                      ├─ Batch processor
                      └─▶ Grafana Cloud OTLP gateway
                              ├─▶ Tempo   (traces)
                              ├─▶ Loki    (logs)
                              └─▶ Mimir   (metrics)
```

## Files

| Path | Purpose |
|------|---------|
| `alloy/config.alloy` | Grafana Alloy River pipeline config |
| `app/app.py` | Flask app — traces + metrics + logs via OTLP |
| `app/requirements.txt` | OTel SDK dependencies |
| `app/Dockerfile` | Python 3.12 slim image |
| `grafana/provisioning/datasources/` | Tempo + Loki + Prometheus datasource config |
| `grafana/provisioning/dashboards/` | Pre-built observability dashboard |
| `docker-compose.yml` | All services (app + alloy + load-gen) |
| `.env.example` | Credential template |

## Quick start

### 1. Get Grafana Cloud credentials

Log in to [grafana.com](https://grafana.com) → your stack → **OpenTelemetry → Configure**.

You need:
- **OTLP Endpoint** — e.g. `https://otlp-gateway-prod-eu-west-0.grafana.net/otlp`
- **Instance ID** — numeric
- **API Key** — service account token with `metrics:write logs:write traces:write`

### 2. Configure

```bash
cd integrations/grafana-alloy
cp .env.example .env
# edit .env with your real credentials
```

### 3. Start

```bash
docker compose --env-file .env up --build
```

The load generator fires traffic every 3 seconds. Signals appear in Grafana Cloud within ~60–90 s.

### 4. Verify

```bash
# Alloy UI (component graph + live pipeline status)
open http://localhost:12346

# App health
curl http://localhost:5001/health

# Trigger a 4-span checkout trace
curl -X POST http://localhost:5001/checkout \
  -H "Content-Type: application/json" \
  -d '{"product_id":"P001","quantity":2}'
```

> Ports are offset from the root DataObs stack to avoid conflicts:
> - App: `5001` (root uses `8080`)
> - Alloy gRPC: `4319` (root uses `4317`)
> - Alloy UI: `12346`

## Port map

| Service | Internal | External | Notes |
|---------|----------|----------|-------|
| alloy-app | 5000 | 5001 | Offset to avoid root stack conflict |
| alloy-collector gRPC | 4317 | 4319 | |
| alloy-collector HTTP | 4318 | 4320 | |
| alloy-collector UI | 12345 | 12346 | |

## Relationship to root DataObs stack

The root `docker-compose.yml` uses the **OTel Collector contrib** image pointing
to Elasticsearch/Kibana. This integration is a **separate, additive stack** that
routes the same OTLP signals to **Grafana Cloud** instead.

You can run both stacks simultaneously — they use isolated Docker networks
(`dataobs-net` vs `alloy-net`) and offset ports.

## Full guide

See [`../../docs/poc-setup.md`](../../docs/poc-setup.md) (if present) or the
[`docs/GUIDE.md`](../grafana-alloy/docs/GUIDE.md) inside this directory
for the complete 10-step walkthrough including Kubernetes migration and alerting rules.
