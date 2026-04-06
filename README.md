<p align="center">
  <strong>DataObs</strong>
</p>

<h1 align="center">DataObs</h1>
<p align="center"><strong>Full-Stack Data Observability Platform</strong></p>
<p align="center">
  Built on <a href="https://opentelemetry.io/">OpenTelemetry</a> + <a href="https://www.elastic.co/">Elasticsearch</a> · Cloud Agnostic · Production-Ready
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-01696f" alt="License"/></a>
  <a href="docs/ARCHITECTURE.md"><img src="https://img.shields.io/badge/docs-architecture-blue" alt="Docs"/></a>
  <a href="https://opentelemetry.io/"><img src="https://img.shields.io/badge/OpenTelemetry-OTEL-orange" alt="OTel"/></a>
</p>

---

## What is DataObs?

**DataObs** is an open, cloud-agnostic data observability platform that gives you end-to-end visibility across your entire data ecosystem — from cloud infrastructure and data pipelines to data quality, lineage, freshness, and business impact.

Inspired by the observability pillars of Datadog, Dynatrace, Splunk, and Monte Carlo, DataObs consolidates everything into a **Four-Tower Architecture** built on OpenTelemetry (for collection) and Elasticsearch (for storage, search, and ML-driven alerting).

---

## The Four Towers

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TOWER 4: BUSINESS OBSERVABILITY                  │
│          KPIs · Revenue Impact · Customer Experience · SLOs         │
└────────────────────────┬───────────────────────────────────────────┘
                         │
         ┌───────────────┴────────────────┐
         ▼                                ▼
┌─────────────────────┐        ┌──────────────────────┐
│  TOWER 1            │        │  TOWER 3              │
│  FULL STACK OBS     │        │  DATA OBSERVABILITY   │
│  Infra · APM · RUM  │        │  Freshness · Quality  │
│  Traces · Logs      │        │  Lineage · Contracts  │
└──────────┬──────────┘        └──────────┬────────────┘
           │                              │
           └──────────────┬───────────────┘
                          ▼
              ┌──────────────────────┐
              │  TOWER 2             │
              │  PIPELINE OBS        │
              │  Lambda · EMR · Glue │
              │  Airflow · Spark     │
              └──────────────────────┘
                          │
         ┌────────────────▼───────────────────┐
         │   UNIFIED TELEMETRY FOUNDATION      │
         │   OpenTelemetry · Elasticsearch     │
         └─────────────────────────────────────┘
```

| Tower | What it answers | Key signals |
|-------|----------------|-------------|
| **Full Stack** | "What is happening with our systems?" | CPU, memory, traces, logs, APM, RUM |
| **Pipeline** | "Are our pipelines running reliably?" | Lambda duration, EMR job status, Glue runs, SLAs |
| **Data** | "Is our data trustworthy?" | Freshness, quality scores, volume drift, schema changes |
| **Business** | "What is the business impact?" | Revenue KPIs, SLA breaches, conversion, churn |

---

## Key Capabilities

| Capability | Description |
|-----------|-------------|
| 🔭 **Infrastructure Observability** | AWS EC2, EKS, ECS, RDS, S3 metrics via OTEL |
| 🔄 **Pipeline Observability** | Lambda, EMR, Glue, Athena, Step Functions instrumentation |
| 📊 **Data Quality** | Row counts, null rates, schema drift, custom rules |
| 🕐 **Data Freshness** | Expected-vs-actual arrival SLAs, delay alerting |
| 🗺️ **Data Lineage** | Automated lineage graph from S3 → Glue → Athena → BI |
| ✅ **Data Validation** | Great Expectations-compatible rule engine |
| 🔔 **Alerting** | ServiceNow, PagerDuty, Slack, OpsGenie, email |
| 🤖 **ML Anomaly Detection** | Elasticsearch ML jobs for metric baselines |
| 🌐 **Cloud Agnostic** | AWS, GCP, Azure, on-prem via OTEL Collector |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- AWS credentials (for AWS data sources, optional)

### 1-Minute Deploy

```bash
# Clone the repository
git clone https://github.com/Jagadeeshck/DataObs.git
cd DataObs

# Start the full stack (Elasticsearch + Kibana + OTEL Collector + DataObs API)
docker compose up -d

# Configure your first data source
cp config/examples/aws-lambda.yaml config/sources/my-lambda.yaml
# Edit my-lambda.yaml with your settings

# Apply configuration
./dataobs configure --source config/sources/my-lambda.yaml

# Open Kibana
open http://localhost:5601
```

### Python SDK

```python
from dataobs import DataObsClient, DataSource, FreshnessRule

client = DataObsClient(endpoint="http://localhost:8080")

# Register a data source
source = DataSource(
    name="sales_orders",
    type="s3",
    location="s3://my-bucket/sales/orders/",
    owner="data-team@company.com"
)
client.register_source(source)

# Define a freshness rule
rule = FreshnessRule(
    source="sales_orders",
    expected_interval_hours=1,
    alert_after_hours=2,
    notify=["slack:#data-alerts", "servicenow:P2"]
)
client.add_rule(rule)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | Platform architecture & design decisions |
| [Installation](docs/INSTALLATION.md) | Full deployment guide (Docker, Helm, bare metal) |
| [AWS Integration](docs/AWS_INTEGRATION.md) | Lambda, EMR, Glue, Athena, RDS, S3 setup |
| [Data Quality](docs/DATA_QUALITY.md) | Validation rules, quality scoring |
| [Data Lineage](docs/DATA_LINEAGE.md) | Lineage tracking & impact analysis |
| [Data Freshness](docs/DATA_FRESHNESS.md) | Freshness monitoring & SLAs |
| [Alerting](docs/ALERTING.md) | ServiceNow, PagerDuty, Slack integration |

---

## Tech Stack

```
Collection:    OpenTelemetry Collector + custom receivers
Storage:       Elasticsearch 8.x (metrics, logs, traces, metadata)
Visualization: Kibana (dashboards, ML, alerts)
API:           Python FastAPI
SDK:           Python, Java, Node.js
Packaging:     Docker, Helm chart
CI/CD:         GitHub Actions
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome!

## License

Apache 2.0 — see [LICENSE](LICENSE).
