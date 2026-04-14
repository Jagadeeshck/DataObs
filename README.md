# DataObs — Cloud-Agnostic Data Observability Platform

[![CI](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml)
[![Release](https://github.com/Jagadeeshck/DataObs/actions/workflows/release.yml/badge.svg)](https://github.com/Jagadeeshck/DataObs/actions/workflows/release.yml)
[![Latest Release](https://img.shields.io/github/v/release/Jagadeeshck/DataObs?sort=semver&logo=github&label=release)](https://github.com/Jagadeeshck/DataObs/releases/latest)
[![GHCR](https://img.shields.io/badge/GHCR-packages-blue?logo=github)](https://github.com/Jagadeeshck?tab=packages&repo_name=DataObs)
[![Trivy Security Scan](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml/badge.svg?branch=main&event=push&label=security-scan)](https://github.com/Jagadeeshck/DataObs/security/code-scanning)
[![Security: Critical CVEs](https://img.shields.io/github/issues/Jagadeeshck/DataObs/security%3Acritical-cve?color=B60205&label=critical%20CVEs&logo=trivy)](https://github.com/Jagadeeshck/DataObs/issues?q=is%3Aopen+label%3Asecurity%3Acritical-cve)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-native-blueviolet?logo=opentelemetry)](https://opentelemetry.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> **DataObs** is a production-ready blueprint and implementation starter for end-to-end observability across infrastructure, data pipelines, data quality/freshness/lineage, and business impact — built on OpenTelemetry with dual back-end support for Elasticsearch/Kibana and Grafana Cloud.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Product Pillars](#product-pillars)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration Reference](#configuration-reference)
- [Integrations](#integrations)
- [Kubernetes & Helm](#kubernetes--helm)
- [CI / GitHub Actions](#ci--github-actions)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

DataObs solves the "dark pipeline" problem: large-scale data platforms emit enormous volumes of telemetry but most of it is never correlated, analysed, or acted on in time to prevent data quality incidents.

This repository provides:

- A **4-pillar observability model** (Full-Stack, Pipeline, Data, Business) as both architectural guidance and runnable code
- **OpenTelemetry-native** instrumentation for Python services, Apache Spark jobs, AWS Lambda, and EC2-hosted runtimes
- A **dual back-end** strategy: Elasticsearch/Kibana for on-prem/hybrid, and Grafana Cloud (Tempo/Loki/Mimir) for SaaS
- **Alerting integrations** for ServiceNow, PagerDuty, and Slack out of the box
- A **Helm chart** and raw Kubernetes manifests for production deployment
- **Terraform modules** for AWS infrastructure provisioning

---

## Architecture

```
                        ┌─────────────────────────────────────────────────────┐
                        │                  Signal Sources                     │
                        │  Python Apps · Spark Jobs · Lambda · EC2 · K8s pods │
                        │  (OTel SDK — semconv resource attributes required)   │
                        └───────────────────────┬─────────────────────────────┘
                                                │  OTLP (gRPC / HTTP)
                        ┌───────────────────────▼─────────────────────────────┐
                        │         OTel Collector / Grafana Alloy               │
                        │  Receive → Semconv enrich → Normalize → Batch → Route│
                        │  spanmetrics connector (RED metrics from traces)      │
                        │  servicegraph connector (topology map)               │
                        └──┬──────────┬───────────────┬──────────┬────────────┘
                           │          │               │          │
          ┌────────────────▼──┐  ┌────▼────────┐  ┌──▼──────┐  ┌──▼──────────────┐
          │ Elasticsearch 8.x │  │  OpenSearch │  │   AMP   │  │  Grafana Cloud  │
          │ AIOps + ML        │  │ self / AWS  │  │(metrics)│  │ OTLP gateway    │
          │ ECS mapping       │  │ via OSIS or │  │         │  │ Tempo/Loki/Mimir│
          │ Kibana dashboards │  │ Data Prepper│  └────┬────┘  └──────────────────┘
          └──────────┬────────┘  └──────┬──────┘       │
                     │                  │         ┌─────▼──────────────────────────┐
                     │                  │         │   Amazon Managed Grafana       │
                     │                  └────────►│   Data sources: AMP + OSIS     │
                     │                            │   Service map · Anomaly detect  │
                     │                            │   Drilldown correlations        │
                     │                            └────────────────────────────────┘
                     │
          ┌──────────▼──────────────────────────────────────────────────────┐
          │                  DataObs Platform                                │
          │  Quality Engine · Freshness SLA · Lineage · Rules API           │
          └──────────────────────────────────┬──────────────────────────────┘
                                             │
          ┌──────────────────────────────────▼──────────────────────────────┐
          │              Alerting & ITSM                                     │
          │         ServiceNow · PagerDuty · Slack                          │
          └──────────────────────────────────────────────────────────────────┘
```

### Backend selector

Set `DATAOBS_BACKEND` to activate the desired sink(s):

| Value | Metrics | Traces | Logs | Use case |
|---|---|---|---|---|
| `elasticsearch` | ES `dataobs-metrics` | ES `dataobs-traces` | ES `dataobs-logs` | Default — local / on-prem AIOps |
| `opensearch` | OpenSearch via Data Prepper | OpenSearch trace-analytics | OpenSearch logs | Self-managed OpenSearch |
| `opensearch_aws` | OSIS → OpenSearch domain | OSIS → OpenSearch domain | OSIS → OpenSearch domain | Amazon OpenSearch Service |
| `aws_grafana` | AMP → Amazon Managed Grafana | OSIS → OpenSearch → AMG | OSIS → OpenSearch → AMG | Full AWS managed stack |
| `grafana_cloud` | Grafana Cloud OTLP | Grafana Cloud OTLP | Grafana Cloud OTLP | Grafana Cloud SaaS |
| `all` | All of the above | All of the above | All of the above | Fan-out / migration |

See [`docs/aws-grafana-setup.md`](docs/aws-grafana-setup.md) for the AWS provisioning walkthrough.

Signal flow for the Grafana Alloy integration:

```
Python Flask App
  └─► OTLP gRPC ──► Grafana Alloy pipeline
                        ├─ Resource detection (host.name, os.type)
                        ├─ Attribute enrichment / cleanup
                        ├─ Batch processor (512 records / 5 s)
                        └─► Grafana Cloud OTLP gateway
                                ├─► Tempo   (traces + service map)
                                ├─► Loki    (logs + trace correlation)
                                └─► Mimir   (metrics + exemplars)
```

---

## Product Pillars

DataObs follows a **4-pillar model** inspired by Datadog, Dynatrace, Monte Carlo, and Collibra:

| Pillar | What it covers | Key signals |
|--------|---------------|-------------|
| **Full-Stack Observability** | Infrastructure, hosts, containers, K8s | CPU, memory, network, pod health |
| **Pipeline Observability** | Spark jobs, Kafka, Lambda, Glue | Records in/out, lag, duration, errors |
| **Data Observability** | Freshness, quality, schema, lineage | SLA breach, null rate, row count drift |
| **Business Observability** | KPIs, SLAs, revenue impact | Order value, conversion, anomaly alerts |

See the detailed model: [`docs/architecture/four-tower-model.md`](docs/architecture/four-tower-model.md)

---

## Repository Layout

```
DataObs/
├── .github/
│   └── workflows/
│       ├── ci.yml                        # CI: validate + test + build + Trivy scan
│       └── release.yml                   # Release: build & push versioned images to GHCR
│
├── src/
│   ├── api/
│   │   └── main.py                       # REST API — rules and lineage management
│   ├── core/
│   │   ├── pillars.py                    # 4-pillar model with maturity scoring
│   │   └── enterprise_blueprint.py       # Enterprise deployment blueprints
│   ├── quality/
│   │   ├── checks/                       # Pluggable data quality checks
│   │   │   ├── base.py
│   │   │   ├── null_check.py
│   │   │   ├── row_count_check.py
│   │   │   ├── schema_check.py
│   │   │   ├── uniqueness_check.py
│   │   │   └── value_range_check.py
│   │   ├── freshness.py                  # Freshness SLA enforcement
│   │   └── lineage.py                    # Data lineage graph + impact analysis
│   ├── alerting/
│   │   ├── servicenow.py                 # ServiceNow incident client
│   │   ├── pagerduty.py                  # PagerDuty Events API client
│   │   └── slack.py                      # Slack webhook alerting
│   └── analytics/
│       └── elasticsearch_ml.py           # ES native ML job helpers
│
├── config/
│   ├── dataobs.example.yaml              # Main platform configuration blueprint
│   ├── otel-collector-config.yaml        # OTel Collector pipelines and exporters
│   ├── otel-ec2-agent-config.yaml        # ADOT EC2 agent config
│   └── elasticsearch/
│       ├── server/                       # ILM, index templates, ingest pipelines
│       └── tenant/                       # Per-tenant OTel overlay configs
│
├── integrations/
│   └── grafana-alloy/                    # Grafana Alloy → Grafana Cloud stack
│       ├── app/                          # Sample Python app (OTel SDK instrumented)
│       ├── alloy/config.alloy            # Grafana Alloy River pipeline config
│       ├── grafana/provisioning/         # Datasources + dashboard JSON
│       ├── docs/GUIDE.md                 # 10-step setup guide
│       └── docker-compose.yml
│
├── k8s/                                  # Raw Kubernetes manifests
├── helm/dataobs/                         # Helm chart for production K8s deployment
│
├── infra/terraform/
│   ├── aws-ec2-otel-agent/               # EC2 OTel agent rollout via SSM
│   └── elasticsearch/                    # ES server and tenant Terraform modules
│
├── docs/
│   ├── architecture/                     # System diagrams and design decisions
│   ├── production/                       # Production runbooks
│   ├── integrations/                     # Integration guides (ServiceNow, etc.)
│   ├── towers/                           # Per-pillar deep-dives
│   └── wiki/                             # Operations wiki
│
├── tests/                                # pytest test suite
├── docker-compose.yml                    # Local full stack (ES + Kibana + OTel + DataObs)
├── Dockerfile.api
├── Dockerfile.quality
├── requirements.txt
└── README.md
```

---

## Prerequisites

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Runtime |
| Docker | 24+ | Local stack |
| Docker Compose | v2.20+ | Orchestration |
| Kubernetes | 1.27+ | Production deployment |
| Helm | 3.12+ | K8s package management |
| Terraform | 1.5+ | AWS infrastructure |
| Grafana Alloy | v1.8+ | OTel collector (Grafana Cloud integration) |

For the Grafana Cloud integration only:
- A [Grafana Cloud](https://grafana.com/auth/sign-up) account (free tier works)
- A service account token with `metrics:write logs:write traces:write` scopes

---

## Quick Start

### Local stack (Elasticsearch + Kibana + OTel Collector)

```bash
git clone https://github.com/Jagadeeshck/DataObs.git
cd DataObs

# Copy and populate configuration
cp config/dataobs.example.yaml config/dataobs.yaml
cp .env.example .env
# Edit .env: set ELASTIC_PASSWORD, KIBANA_PASSWORD, etc.

# Start full stack
docker compose up -d

# Verify
curl http://localhost:8080/health          # DataObs API
open http://localhost:5601                 # Kibana
```

### Grafana Cloud integration (Alloy + Tempo + Loki + Mimir)

```bash
cd integrations/grafana-alloy
cp .env.example .env
# Edit .env: GRAFANA_CLOUD_OTLP_ENDPOINT, GRAFANA_CLOUD_INSTANCE_ID, GRAFANA_CLOUD_API_KEY

docker compose --env-file .env up --build
```

The load generator fires traffic immediately. Traces, logs, and metrics appear in Grafana Cloud within ~90 seconds.

```bash
# Verify Alloy pipeline health
open http://localhost:12346          # Alloy UI — component graph

# Trigger a 4-span checkout trace
curl -X POST http://localhost:5001/checkout \
  -H "Content-Type: application/json" \
  -d '{"product_id":"P001","quantity":2}'
```

See [`integrations/grafana-alloy/docs/GUIDE.md`](integrations/grafana-alloy/docs/GUIDE.md) for the complete 10-step walkthrough.

---

## Configuration Reference

### `config/dataobs.example.yaml`

The main platform configuration. Copy to `config/dataobs.yaml` before starting.

| Section | Key fields | Description |
|---------|-----------|-------------|
| `elasticsearch` | `url`, `user`, `password`, `index_prefix` | ES connection and index naming |
| `otel` | `endpoint`, `service_name`, `environment` | OTLP exporter settings |
| `quality` | `checks`, `sla_thresholds`, `schedule` | Quality check rules and SLA config |
| `freshness` | `tables`, `max_age_hours` | Per-table freshness SLA definitions |
| `lineage` | `graph_index`, `impact_depth` | Lineage graph settings |
| `alerting.servicenow` | `instance`, `user`, `password`, `assignment_group` | ServiceNow connection |
| `alerting.pagerduty` | `routing_key`, `severity_map` | PagerDuty routing |
| `alerting.slack` | `webhook_url`, `channel` | Slack notifications |

### Environment variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `ELASTIC_PASSWORD` | Yes | Elasticsearch `elastic` user password |
| `KIBANA_PASSWORD` | Yes | Kibana system user password |
| `GRAFANA_CLOUD_OTLP_ENDPOINT` | Alloy integration | Grafana Cloud OTLP gateway URL |
| `GRAFANA_CLOUD_INSTANCE_ID` | Alloy integration | Numeric Grafana Cloud stack ID |
| `GRAFANA_CLOUD_API_KEY` | Alloy integration | Service account token |
| `OTEL_SERVICE_NAME` | No | Override service name (default: `dataobs-api`) |
| `DEPLOYMENT_ENVIRONMENT` | No | `development` / `staging` / `production` |

---

## Integrations

### Grafana Alloy → Grafana Cloud

Full OTel signal pipeline: metrics, logs, and traces from a Python app → Grafana Alloy collector → Grafana Cloud (Tempo / Loki / Mimir).

**Features:**
- Service map (automatic from span relationships)
- Anomaly detection (Grafana Application Observability)
- Trace → log → metric drilldown correlation
- Auto-formatted Alloy River config (validated in CI with `alloy fmt --test`)
- Load generator for immediate realistic signal volume

**Port map (offset from root stack):**

| Service | External port |
|---------|--------------|
| Sample app | `5001` |
| Alloy gRPC | `4319` |
| Alloy HTTP | `4320` |
| Alloy UI | `12346` |

Location: [`integrations/grafana-alloy/`](integrations/grafana-alloy/)

### ServiceNow

Automatic incident creation from data quality failures. Supports priority mapping, assignment groups, and resolution callbacks.

Guide: [`docs/integrations/servicenow.md`](docs/integrations/servicenow.md)

### PagerDuty

Events API v2 integration with severity mapping from DataObs pillar signals to PagerDuty urgency levels.

### Slack

Webhook-based alerting with structured message blocks. Supports per-channel routing by pillar or severity.

---

## Kubernetes & Helm

### Raw manifests

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/otel-collector.yaml
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/deployment-quality.yaml
kubectl apply -f k8s/service-api.yaml
```

### Helm chart

```bash
helm repo add dataobs ./helm
helm install dataobs ./helm/dataobs \
  --namespace dataobs --create-namespace \
  --set elasticsearch.url=http://elasticsearch:9200 \
  --set elasticsearch.password=<password> \
  --set otel.endpoint=http://alloy:4317
```

See [`helm/dataobs/README.md`](helm/dataobs/README.md) for all `values.yaml` options.

### Grafana Alloy on Kubernetes

Replace the Docker Compose Alloy service with a Helm DaemonSet:

```bash
helm repo add grafana https://grafana.github.io/helm-charts && helm repo update

helm install alloy grafana/alloy \
  --namespace monitoring --create-namespace \
  --set-file alloy.configMap.content=integrations/grafana-alloy/alloy/config.alloy \
  --set env[0].name=GRAFANA_CLOUD_OTLP_ENDPOINT \
  --set env[0].value="$GRAFANA_CLOUD_OTLP_ENDPOINT" \
  --set env[1].name=GRAFANA_CLOUD_INSTANCE_ID \
  --set env[1].value="$GRAFANA_CLOUD_INSTANCE_ID" \
  --set env[2].name=GRAFANA_CLOUD_API_KEY \
  --set env[2].value="$GRAFANA_CLOUD_API_KEY"
```

---

## CI / GitHub Actions

The repo ships two workflows.

### CI workflow (`ci.yml`)

Runs on every push and PR:

| Job | Trigger | What it does |
|-----|---------|-------------|
| `validate-configs` | All branches | `alloy fmt --test`, YAML lint, dashboard JSON lint, Python syntax check |
| `test-python` | After validate | `pytest` suite — 12 tests across quality checks, API, alerting, analytics |
| `build-docker` | After validate | Builds `dataobs/api`, `dataobs/quality`, `dataobs/sample-python-app` with GHA layer cache |
| `security-scan` | `main` only | Trivy CVE scan (JSON + table + SARIF) with auto-issue creation |

### Security scan — auto-issue workflow

---

### Release workflow (`release.yml`)

Triggered by a `v*.*.*` tag push (e.g. `git tag v1.0.0 && git push --tags`).

| Job | What it does |
|-----|-------------|
| `build-and-push` (matrix × 3) | Builds and pushes `dataobs-api`, `dataobs-quality`, `dataobs-sample-app` to GHCR with semver tags + `:latest` |
| `create-release` | Generates a changelog from git log, creates a GitHub Release with pull instructions and Helm/K8s update notes |

**Tags published per image:**

```
ghcr.io/jagadeeshck/dataobs-api:1.2.3    # exact version
ghcr.io/jagadeeshck/dataobs-api:1.2      # minor alias
ghcr.io/jagadeeshck/dataobs-api:1        # major alias
ghcr.io/jagadeeshck/dataobs-api:latest   # always newest release
```

Images include [SBOM attestations](https://docs.docker.com/build/metadata/attestations/sbom/) and [SLSA build provenance](https://docs.docker.com/build/metadata/attestations/slsa-provenance/).

Pre-release tags (e.g. `v1.0.0-rc.1`) are marked as pre-release automatically.

**To cut a release:**

```bash
git tag v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### Security scan — auto-issue workflow

```
CRITICAL CVEs found?
  YES, open issue exists? → add comment with new CVE table + run link
  YES, no open issue?    → create issue: label security:critical-cve, assign actor
  NO CRITICALs           → auto-close open issue with resolution comment
```

The [![Security: Critical CVEs](https://img.shields.io/github/issues/Jagadeeshck/DataObs/security%3Acritical-cve?color=B60205&label=critical%20CVEs&logo=trivy)](https://github.com/Jagadeeshck/DataObs/issues?q=is%3Aopen+label%3Asecurity%3Acritical-cve) badge shows the live open-issue count.

---

## Roadmap

### In progress
- [ ] Column distribution drift checks with dynamic thresholds
- [ ] End-to-end integration tests for API + alert delivery paths
- [ ] Elasticsearch-backed persistence for API (replace in-memory store)

### Planned
- [ ] Spark job instrumentation examples (PySpark + OTel SDK)
- [ ] AWS Lambda OTel layer for serverless data pipelines
- [ ] dbt integration — surface model run results as OTel spans
- [ ] Monte Carlo-style automated anomaly detection on metric histograms
- [ ] Multi-tenant config management with per-tenant Alloy overlays
- [ ] Grafana dashboard provisioning via Terraform (Grafana provider)
- [ ] GitHub Actions: auto-PR for Dependabot security fixes
- [ ] OpenSearch migration path (config + index template equivalents)

### Completed
- [x] 4-pillar observability model and core quality checks
- [x] Grafana Alloy → Grafana Cloud integration (metrics + logs + traces)
- [x] ServiceNow, PagerDuty, Slack alerting clients
- [x] Helm chart + raw K8s manifests
- [x] Terraform modules for AWS EC2 OTel agent rollout
- [x] CI pipeline: validate + test + Docker build + Trivy security scan
- [x] Auto-issue creation on CRITICAL CVEs with auto-close on resolution
- [x] README badges: CI status, Trivy scan, critical CVE count

---

## Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a PR.

**Quick contribution flow:**

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/DataObs.git
cd DataObs

# 2. Create a feature branch
git checkout -b feat/your-feature-name

# 3. Install dependencies
pip install -r requirements.txt pytest

# 4. Make changes, run tests
python -m pytest tests/ -v

# 5. Open a PR against main
```

All PRs must pass the full CI pipeline (validate → test → build) before merge.

---

## License

This project is licensed under the [MIT License](LICENSE).
