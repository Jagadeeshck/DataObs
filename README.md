
## Elasticsearch-native product architecture

```text
Sources
  ├── Elastic Agent/Fleet and existing Elastic integrations
  ├── Elastic Agent as EDOT / standalone EDOT
  └── DataObs Scanner and Connector SDK
              ↓
DataObs Gateway and Product APIs
              ↓
Elasticsearch
  ├── append-only data streams
  ├── versioned mutable state indices
  ├── transforms/latest-state projections
  └── analytical queries and alerting
              ↓
Kibana + Elastic Workflows + future DataObs Console
```

DataObs product state is Elasticsearch-native. In production, `DATAOBS_STORE_BACKEND=elasticsearch` is mandatory; local and test mode may continue to use in-memory state. The canonical architecture is the [six-pillar product model](docs/architecture/six-pillar-product-model.md), not the deprecated four-tower model.

### Optional Exporters and Legacy Integrations

OpenSearch, Grafana Cloud, AMP, AMG, Grafana Alloy, and other exporters are optional integrations for telemetry copies or legacy demonstrations. They must not store authoritative DataObs product state, and `DATAOBS_BACKEND=all` is not a normal product operating mode. POC and demo assets remain isolated from product runtime.

# DataObs

## Elasticsearch-native six-pillar architecture

DataObs uses Elasticsearch and Kibana as the authoritative investigation plane for six pillars: data quality, freshness, schema drift, profiling, lineage impact and operational health. Elastic Agent/Fleet/EDOT remain responsible for generic telemetry, while the DataObs Scanner performs PostgreSQL metadata discovery, schema snapshots, freshness checks and opt-in aggregate profiling. Mutable tenant-aware current state is stored in versioned Elasticsearch aliases; immutable inventory, snapshot, change, profile, freshness, audit and scanner-health facts are written to data streams. Production deployments must configure Elasticsearch storage and fail readiness instead of silently falling back to memory.

Optional Exporters and Legacy Integrations: Grafana, OpenSearch and Alloy examples remain available for migration and interoperability scenarios, but they are not the authoritative DataObs product plane.
 — Cloud-Agnostic Data Observability Platform

[![CI](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml)
[![Release](https://github.com/Jagadeeshck/DataObs/actions/workflows/release.yml/badge.svg)](https://github.com/Jagadeeshck/DataObs/actions/workflows/release.yml)
[![Latest Release](https://img.shields.io/github/v/release/Jagadeeshck/DataObs?sort=semver&logo=github&label=release)](https://github.com/Jagadeeshck/DataObs/releases/latest)
[![GHCR](https://img.shields.io/badge/GHCR-packages-blue?logo=github)](https://github.com/Jagadeeshck?tab=packages&repo_name=DataObs)
[![Trivy Security Scan](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml/badge.svg?branch=main&event=push&label=security-scan)](https://github.com/Jagadeeshck/DataObs/security/code-scanning)
[![Security: Critical CVEs](https://img.shields.io/github/issues/Jagadeeshck/DataObs/security%3Acritical-cve?color=B60205&label=critical%20CVEs&logo=trivy)](https://github.com/Jagadeeshck/DataObs/issues?q=is%3Aopen+label%3Asecurity%3Acritical-cve)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-native-blueviolet?logo=opentelemetry)](https://opentelemetry.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> DataObs is being productised as an Elasticsearch-native Data Observability and Data Streams Monitoring platform. Elasticsearch and Kibana are the primary analytical and investigation platform; OpenTelemetry and OpenLineage are the ingestion standards. Optional exporters and legacy POC paths remain isolated integrations.

> The repository is under active productisation and is not yet a production release.

> Governance: [Productization Master Plan](docs/product/dataobs-productization-master-plan.md), [Agent and Collection Plane Architecture](docs/architecture/dataobs-agent-and-collection-plane.md), and [Phase 0 Closure Report](docs/development/open-issue-closure-report.md).
---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Product Pillars](#product-pillars)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Troubleshooting](#troubleshooting)
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

- An Elasticsearch-native product direction for data observability, pipeline/job observability, streams monitoring, lineage, incident response, and product-quality visualisation
- **OpenTelemetry-native** instrumentation for Python services, Apache Spark jobs, AWS Lambda, and EC2-hosted runtimes
- Elasticsearch/Kibana as the primary analytical and investigation platform, with optional exporters and legacy POC paths isolated as integrations
- **Alerting integrations** for ServiceNow, PagerDuty, and Slack out of the box
- A **Helm chart** and raw Kubernetes manifests for deployment experimentation and validation
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
          │ Elasticsearch 9.x │  │  OpenSearch │  │   AMP   │  │  Grafana Cloud  │
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

See the detailed model: [`docs/architecture/six-pillar-product-model.md`](docs/architecture/six-pillar-product-model.md)

---

## Repository Layout

DataObs separates production modules, proof-of-concept helpers, deployment assets, integrations, and documentation so new features have an obvious home. See the maintainer-focused [repository structure and feature-development guide](docs/development/repository-structure.md) for extension points, quality-check registration, and issue-readiness notes.

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

## Troubleshooting

### ❌ Elasticsearch fails to start — "cannot upgrade a node from version [8.x] directly to version [9.x]"

**Symptom**

```
fatal exception while booting Elasticsearch
error.message: cannot upgrade a node from version [8.13.0] directly to version [9.x],
               upgrade to version [8.19.0] first.
```

**Root cause**

Elasticsearch stores its originating version in node metadata inside the `esdata` Docker volume. When you previously ran the stack with an older image (e.g. `8.13.0`) and later pulled the current 9.x POC image, the new process reads the stale metadata and hard-blocks the start because Elastic enforces a **mandatory stepping-stone upgrade path**: you cannot skip directly from 8.x to 9.x — you must first pass through the last minor release of 8.x (`8.19.0`). Since this is a local POC with no production data, the simplest fix is to delete the stale volume.

**Fix — delete the stale `esdata` volume**

```bash
# 1. Tear down all running containers
docker compose down

# 2. Confirm the exact volume name (usually prefixed with your folder name)
docker volume ls | grep esdata

# 3. Remove the stale volume
docker volume rm dataobs_esdata

# 4. Ensure .env is populated
cp .env.example .env
# Edit .env — set ELASTIC_PASSWORD and KIBANA_PASSWORD

# 5. Re-start the stack from scratch
docker compose up -d
```

**Verify the fix**

```bash
# Watch ES boot — should report version 9.x with no errors
docker logs dataobs-es01 -f

# Confirm the running version
curl -s -u elastic:<your-password> http://localhost:9200 | jq .version.number
# Expected output: "9.4.2"
```

Kibana will be available at `http://localhost:5601` once the `es-setup` init container completes its one-shot password bootstrap and the `service_completed_successfully` health gate opens for the Kibana service.

> **Note:** This error can also appear if you restore an old `esdata` volume backup from a previous major version. The same fix applies — either delete the volume (POC) or perform the intermediate 8.19.0 upgrade step first (production).

---

### ❌ `es-setup` container exits with non-zero code

**Symptom:** `dataobs-es-setup` exits with error `Failed to set kibana_system password (HTTP 401)`.

**Cause:** `ELASTIC_PASSWORD` in `.env` does not match the password that was used when the `esdata` volume was first initialised.

**Fix:** Either update `.env` to match the original password, or delete the `esdata` volume (see above) and restart with a fresh password.

---

### ❌ Kibana shows "Kibana server is not ready yet"

**Symptom:** Browser shows the Kibana loading screen indefinitely.

**Cause:** Kibana depends on `es-setup` completing successfully. If `es-setup` failed, Kibana's `depends_on: service_completed_successfully` gate never opens.

**Fix:**

```bash
# Check es-setup logs first
docker logs dataobs-es-setup

# Then check Kibana logs
docker logs dataobs-kibana
```

Resolve any `es-setup` error first (see above), then restart:

```bash
docker compose restart kibana
```

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


## Configuration
See `docs/production/configuration.md` for mode-aware and production-safe settings.

## Phase 0 collection-plane architecture

The DataObs Agent experience is defined as a collection plane that reuses Elastic Agent/Fleet integrations and EDOT by default, adding the DataObs Scanner only for data-observability scanning capabilities such as schema snapshots, freshness, profiling, quality, and lineage. See `docs/architecture/dataobs-agent-and-collection-plane.md`.

## PostgreSQL Data Observability vertical slice

This repository now treats Elasticsearch and Kibana as the authoritative runtime for the PostgreSQL data-observability slice while keeping local in-memory state for unit tests only. The implemented slice is metadata-first: the scanner reads PostgreSQL catalog metadata and opt-in aggregate measurements, emits immutable inventory/schema/freshness/profile events, and updates current-state documents without persisting raw rows.

Supported PostgreSQL capabilities in this gate:

- real `psycopg` connection testing with secret-reference-only passwords (`env://`, `file://`, and `k8s-file://`);
- catalog discovery through explicit `pg_catalog` and `information_schema` projections for schemas, table-like relations, columns, owners, comments, sizes, constraints, indexes, partitions, and analyze metadata where privileges allow it;
- deterministic schema canonicalization and fingerprinting;
- configurable freshness measurement through approved timestamp columns, external watermarks, and low-confidence catalog fallback;
- opt-in aggregate profiling with read-only transactions, statement timeouts, identifier validation, sensitive-column denial, and no raw-row persistence;
- scanner CLI commands for capabilities, connection tests, discovery, one-shot task execution, and heartbeat loop;
- Elasticsearch task updates using `_seq_no` and `_primary_term` compare-and-set tokens instead of `_version` locks;
- migration `0002_postgres_observability` resources applied from migration-specific operations with checksum verification and dependency ordering;
- a Docker Compose demo stack containing PostgreSQL, Elasticsearch 9.4.2, Kibana 9.4.2, an OTel collector, the API, and the scanner.

Demo quick start:

```bash
docker compose -f docker-compose.postgres-demo.yml up -d --build
./bin/dataobs elastic apply
./scripts/demo_postgres_vertical_slice.sh
docker compose -f docker-compose.postgres-demo.yml down -v
```

The demo seeds tables, constraints, indexes, a partitioned table, a view, a materialized view, runs scanner operations, alters schema, checks discovery/schema/profile evidence, and scans outputs for the sentinel secret. The demo password is mounted as a Docker secret from `config/postgres-demo-password.txt`; production deployments should replace this with a managed secret file or platform secret reference and should not enable unauthenticated development mode.

Least-privilege SQL remains intentionally narrow: grant database connect, schema usage, catalog visibility, and table `SELECT` only for assets whose freshness/profile policies are enabled. If catalog/statistics privileges are unavailable, scanners preserve nullable fields and emit capability warnings rather than failing the entire scan.

Task lifecycle: Collection Manager generates available tasks from enabled scan policies. Scanners claim tasks using an Elasticsearch compare-and-set update, renew leases while running, submit idempotent results, and transition failures through retryable or dead-letter states. Expired leases can be reclaimed; active leases cannot be stolen.

Limitations: this PR does not make DataObs production-ready. Full OIDC enforcement, broad lineage extraction from PostgreSQL logs, automated remediation, Elastic Streams/Workflows incident response, and non-PostgreSQL database slices remain future milestones.

## Incident automation vertical slice

DataObs now includes a draft Elastic Workflows incident-automation slice: `0003_incident_automation` mappings, versioned Finding/Incident/Workflow contracts, deterministic incident manager services, public-Kibana workflow tooling, alert-rule binding assets, optional Streams enrichment, safe-action/approval APIs, and a Docker demo. This does not make DataObs production-ready and does not enable autonomous or destructive remediation.

## Kafka Data Streams Monitoring (first vertical slice)

DataObs now includes a read-only Kafka Observer foundation, deterministic OTel messaging pathway semantics, lag/retention-risk calculations, migration `0004`, tenant-scoped projection APIs, and controlled workflow templates. See [the architecture](docs/architecture/kafka-data-streams-monitoring.md) and [least-privilege guide](docs/operations/kafka-least-privilege.md). This does not make DataObs production-ready; real Kafka/Elasticsearch/Kibana integration validation remains required.
