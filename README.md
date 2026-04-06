# DataObs — Cloud-Agnostic Data Observability Platform

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
- `docs/wiki/operations-wiki.md`: operations wiki / runbook starter
- `docs/api/rules-and-lineage-api.md`: API usage for rule/lineage management
- `docs/product/data-checks-and-competitive-parity.md`: data check strategy and parity roadmap
- `docs/product/enterprise-contract-playbook.md`: competitive positioning and contract-winning rollout playbook
- `k8s/`: raw Kubernetes manifests for API, quality engine, and OTEL collector
- `helm/dataobs/`: Helm chart for configurable Kubernetes deployments

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
