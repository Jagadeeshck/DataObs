# DataObs — Cloud-Agnostic Data Observability Platform

[![CI](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml)
[![Trivy Security Scan](https://github.com/Jagadeeshck/DataObs/actions/workflows/ci.yml/badge.svg?branch=main&event=push&label=security-scan)](https://github.com/Jagadeeshck/DataObs/security/code-scanning)
[![Security: Critical CVEs](https://img.shields.io/github/issues/Jagadeeshck/DataObs/security%3Acritical-cve?color=B60205&label=critical%20CVEs&logo=trivy)](https://github.com/Jagadeeshck/DataObs/issues?q=is%3Aopen+label%3Asecurity%3Acritical-cve)

DataObs is a product blueprint and implementation starter for end-to-end observability across:
- infrastructure,
- data pipelines,
- data quality/freshness/lineage,
- and business impact.

It is built around **OpenTelemetry** for telemetry collection and **Elasticsearch/Kibana** for storage, analysis, and dashboards.

## Product Pillars

DataObs follows a 4-pillar model inspired by platforms like Datadog, Dynatrace, Splunk, and Monte Carlo:

1. **Full-Stack Observability**
2. **Pipeline Observability**
3. **Data Observability**
4. **Business Observability**

See detailed model documentation:
- [`docs/architecture/four-tower-model.md`](docs/architecture/four-tower-model.md)
- [`docs/architecture/overview.md`](docs/architecture/overview.md)
- [`docs/architecture/system-diagram.md`](docs/architecture/system-diagram.md)

## What is included in this repository

### Runtime and configuration
- `docker-compose.yml`: local stack (Elasticsearch, Kibana, OTEL Collector, DataObs services)
- `config/dataobs.example.yaml`: main configuration blueprint
- `config/otel-collector-config.yaml`: OTEL Collector pipelines and exporters
- `config/otel-ec2-agent-config.yaml`: OTEL/ADOT EC2 agent config for host + app telemetry forwarding

### Core data observability code
- `src/quality/freshness.py`: freshness SLA checks
- `src/quality/lineage.py`: lineage graph ingest and impact analysis
- `src/quality/checks/*`: reusable data quality checks
- `src/core/pillars.py`: pillar/capability model with maturity scoring
- `src/api/main.py`: lightweight HTTP API for rules and lineage management

### Integrations
- `src/alerting/servicenow.py`: ServiceNow incident client
- `src/alerting/pagerduty.py`: PagerDuty Events API client
- `src/alerting/slack.py`: Slack webhook alerting client
- `docs/integrations/servicenow.md`: setup and operating guide
- `src/analytics/elasticsearch_ml.py`: Elasticsearch native ML job helpers

### Production operations
- `docs/production/production-guide.md`: production deployment patterns
- `docs/production/ec2-otel-agent.md`: EC2 instrumentation runbook (Java/Python/Spark + X-Ray option)
- `docs/wiki/operations-wiki.md`: operations wiki / runbook starter
- `docs/api/rules-and-lineage-api.md`: API usage for rule/lineage management
- `docs/product/data-checks-and-competitive-parity.md`: data check strategy and parity roadmap
- `docs/product/enterprise-contract-playbook.md`: competitive positioning and contract-winning rollout playbook
- `k8s/`: raw Kubernetes manifests for API, quality engine, and OTEL collector
- `helm/dataobs/`: Helm chart for configurable Kubernetes deployments
- `infra/terraform/aws-ec2-otel-agent/`: Terraform + SSM rollout for OTEL agent installation/config on EC2

## Quick Start

```bash
git clone https://github.com/Jagadeeshck/DataObs.git
cd DataObs
cp config/dataobs.example.yaml config/dataobs.yaml
docker-compose up -d
```

Then open Kibana at `http://localhost:5601`.

## Key goals
- **Cloud agnostic** architecture (AWS, Azure, GCP, hybrid)
- **OpenTelemetry-native** telemetry contracts
- **Fast onboarding** with declarative config
- **ITSM-ready alerting** with ServiceNow and other channels
- **ML-ready detection** using Elasticsearch native ML jobs

## Next implementation steps
- Add Elasticsearch-backed repositories for API persistence
- Add column distribution drift checks and dynamic thresholds
- Add end-to-end integration tests for API + alert delivery paths
- Expand `/strategy/enterprise-backlog` to persist account-level roadmap plans per customer

---

## Integrations

### Grafana Alloy → Grafana Cloud

A deployable Docker Compose stack that routes all three OTel signals (metrics, logs, traces)
from a sample Python app through **Grafana Alloy** to **Grafana Cloud**
(Tempo / Loki / Mimir), with service maps, anomaly detection, and drilldown correlation.

- **Location**: [`integrations/grafana-alloy/`](integrations/grafana-alloy/)
- **Guide**: [`integrations/grafana-alloy/docs/GUIDE.md`](integrations/grafana-alloy/docs/GUIDE.md)

```bash
cd integrations/grafana-alloy
cp .env.example .env   # add Grafana Cloud credentials
docker compose --env-file .env up --build
```

Signals appear in Grafana Cloud within ~90 seconds. The stack runs on offset ports
(app: `5001`, Alloy gRPC: `4319`) so it can coexist alongside the root DataObs stack.

---

## CI / GitHub Actions

The `.github/workflows/ci.yml` pipeline runs on every push and PR:

| Job | What it checks |
|-----|---------------|
| `validate-configs` | Alloy config syntax (`alloy fmt`), YAML lint, dashboard JSON, Python syntax |
| `test-python` | Full `pytest` suite for DataObs + OTel app |
| `build-docker` | Builds all three Docker images (api, quality, sample-python-app) with GHA layer cache |
| `security-scan` | Trivy CVE scan (`main` only) — JSON + table + SARIF outputs |

### Security scan details

The `security-scan` job runs three Trivy passes against `dataobs/sample-python-app`:

1. **JSON** — parsed by a Python script to extract CRITICAL CVEs and build a structured report
2. **Table** — printed to the Actions log for quick human review
3. **SARIF** — uploaded to the [GitHub Security / Code Scanning tab](https://github.com/Jagadeeshck/DataObs/security/code-scanning)

**Auto-issue workflow:**
- If **CRITICAL CVEs are found** → a GitHub Issue is opened (or an existing one updated with a comment) with a full CVE table, affected packages, fixed versions, and a link to the CI run. The issue is labelled `security:critical-cve` and assigned automatically.
- If a subsequent scan finds **no CRITICALs** → the open issue is auto-closed with a resolution comment.

The [![Security: Critical CVEs](https://img.shields.io/github/issues/Jagadeeshck/DataObs/security%3Acritical-cve?color=B60205&label=critical%20CVEs&logo=trivy)](https://github.com/Jagadeeshck/DataObs/issues?q=is%3Aopen+label%3Asecurity%3Acritical-cve) badge at the top of this README shows the live count of open critical CVE issues at a glance.
