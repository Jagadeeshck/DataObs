# DataObs — Enterprise Data Observability Platform

> **Unified observability from infrastructure to business impact — built on OpenTelemetry and Elasticsearch**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Powered-orange)](https://opentelemetry.io)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.x-green)](https://www.elastic.co)
[![Cloud Agnostic](https://img.shields.io/badge/Cloud-Agnostic-blueviolet)](#cloud-integrations)

---

## What is DataObs?

**DataObs** is a cloud-agnostic, open-standards data observability platform that gives you complete visibility across your entire data estate — from raw infrastructure health all the way up to business KPI impact.

Inspired by the observability approaches of **Datadog**, **Dynatrace**, **Splunk**, and **Monte Carlo**, DataObs goes further by unifying _infrastructure_, _pipeline_, _data quality_, and _business_ observability into a single coherent product — without vendor lock-in.

**Core Technology Stack:**
- 🔭 **OpenTelemetry** — universal telemetry collection (traces, metrics, logs, events)
- 🔍 **Elasticsearch / Kibana** — central telemetry store, analytics, and visualization
- ☁️ **Cloud-agnostic** — AWS, GCP, Azure, on-prem, hybrid
- 🔔 **ServiceNow + PagerDuty + Slack** — built-in alerting integrations

---

## The Four-Tower Framework

DataObs is organized around **four observability towers** — each answering a distinct question about your systems and data:

```
┌─────────────────────────────────────────────────────────────────┐
│                   BUSINESS OBSERVABILITY TOWER                  │
│         Revenue · Customer Experience · KPIs · Decisions        │
└───────────────────┬─────────────────────────────────────────────┘
                    │ Depends on data quality, pipelines & system health
     ┌──────────────▼──────────────┐  ┌─────────────────────────────┐
     │  FULL STACK OBSERVABILITY   │  │   DATA OBSERVABILITY TOWER  │
     │                             │  │                             │
     │  · Infrastructure (EC2/EKS) │  │  · Data Freshness           │
     │  · APM / Distributed Traces │  │  · Data Quality & Integrity │
     │  · RUM / User Experience    │  │  · Schema Evolution         │
     │  · Logs & Security Events   │  │  · Data Lineage             │
     └─────────────▲───────────────┘  └──────────────▲──────────────┘
                   │                                  │
                   │    Relies on healthy pipelines   │
                   └─────────────┬────────────────────┘
                                 │
                   PIPELINE OBSERVABILITY TOWER
          (Lambda · EMR · Glue · Airflow · Kafka · dbt · CI/CD)
                                 │
                    Unified Telemetry Foundation
          (Metrics · Logs · Traces · Events · Metadata · Lineage)
```

| Tower | Core Question | Primary Users |
|---|---|---|
| **Full Stack** | What is happening with our systems? | SRE, Platform Eng |
| **Pipeline** | Are our critical flows running on time? | Data Eng, DevOps |
| **Data** | Is our data trustworthy? | Data Teams, Analytics |
| **Business** | What is the business impact? | Execs, Product, BI |

---

## Key Capabilities

### 🏗️ Full Stack Observability
- Infrastructure monitoring: EC2, EKS, RDS, S3, Lambda, EMR, Glue, Athena
- Kubernetes pod/node/namespace health
- APM with distributed tracing (OpenTelemetry auto-instrumentation)
- Log aggregation with ML anomaly detection
- Cloud cost and capacity observability

### 🔄 Pipeline Observability
- AWS Glue job monitoring (run duration, DPU cost, error rates)
- AWS Lambda invocations, cold starts, throttles, errors
- EMR cluster health and stage-level metrics
- Airflow / Step Functions workflow SLA tracking
- Kafka / Kinesis stream lag and throughput
- CI/CD pipeline health (DORA metrics)

### 📊 Data Observability
- **Data Freshness** — automatic staleness detection per table/dataset
- **Data Volume** — row count anomaly detection with ML baselines
- **Data Quality** — null rates, uniqueness, referential integrity, custom rules
- **Schema Changes** — instant alerts on breaking schema evolution
- **Data Lineage** — end-to-end lineage graph from source → transformation → consumer
- **Data Contracts** — SLA/SLO definition and enforcement per dataset

### 💼 Business Observability
- Business KPI tracking tied to data and pipeline SLAs
- Revenue impact estimation from data incidents
- Customer journey observability
- Compliance and audit evidence generation
- Executive dashboards with cross-tower correlation

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                  │
│  AWS Lambda · EMR · Glue · Athena · RDS · S3 · EC2 · EKS · Kafka    │
│  GCP BigQuery · Azure ADF · On-Prem Hadoop · dbt · Airflow            │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
            ┌───────────────────▼──────────────────┐
            │     OPENTELEMETRY COLLECTOR LAYER     │
            │  · OTEL Collectors (DaemonSet/Sidecar)│
            │  · DataObs Receivers (custom)         │
            │  · Processors (enrichment, sampling)  │
            │  · Exporters (Elasticsearch, OTLP)    │
            └───────────────────┬──────────────────┘
                                │
            ┌───────────────────▼──────────────────┐
            │         ELASTICSEARCH CLUSTER         │
            │  · Telemetry indices (metrics/logs)   │
            │  · Data quality indices               │
            │  · Lineage graph store                │
            │  · ILM for cost-efficient retention   │
            └───────────────────┬──────────────────┘
                                │
     ┌──────────────────────────▼─────────────────────────┐
     │              DATAOBS CORE ENGINE                    │
     │  · Quality Checker · Freshness Monitor              │
     │  · Lineage Tracker · Schema Registry                │
     │  · Anomaly Detector · Alert Manager                 │
     └──────────────────────────┬─────────────────────────┘
                                │
     ┌──────────────────────────▼─────────────────────────┐
     │           VISUALIZATION & INTEGRATIONS             │
     │  Kibana Dashboards · DataObs UI                    │
     │  ServiceNow · PagerDuty · Slack · Email            │
     └─────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- AWS credentials (for AWS integrations)

### 1. Clone & Start

```bash
git clone https://github.com/Jagadeeshck/DataObs.git
cd DataObs

# Copy and configure
cp config/dataobs.example.yaml config/dataobs.yaml
# Edit config/dataobs.yaml with your settings

# Start the full stack
docker-compose up -d
```

### 2. Access Kibana
Open [http://localhost:5601](http://localhost:5601) — pre-built DataObs dashboards load automatically.

### 3. Configure Your First Data Source

```yaml
# config/dataobs.yaml
sources:
  - name: "production-glue"
    type: aws_glue
    region: eu-west-1
    databases: ["analytics", "raw"]
    
  - name: "prod-rds"
    type: aws_rds
    connection_string: "${RDS_CONNECTION_STRING}"
    tables: ["orders", "customers", "events"]

quality_rules:
  - dataset: "prod-rds.orders"
    checks:
      - type: freshness
        max_age_minutes: 60
      - type: row_count
        min_rows: 1000
      - type: null_check
        columns: ["order_id", "customer_id"]
        max_null_pct: 0.0
```

### 4. Run Your First Quality Scan

```bash
python -m dataobs scan --source production-glue --output elasticsearch
```

---

## Repository Structure

```
DataObs/
├── README.md                       # This file
├── docker-compose.yml              # Full stack local deployment
├── config/
│   ├── dataobs.example.yaml        # Main configuration template
│   ├── otel-collector-config.yaml  # OpenTelemetry Collector config
│   └── elasticsearch/
│       ├── index-templates/        # ES index templates
│       └── ilm-policies/           # ILM retention policies
├── docs/
│   ├── architecture/
│   │   ├── overview.md             # Full architecture overview
│   │   ├── four-tower-model.md     # The four-tower framework
│   │   └── tech-stack.md           # Technology decisions
│   ├── towers/
│   │   ├── full-stack.md           # Full Stack Observability guide
│   │   ├── pipeline.md             # Pipeline Observability guide
│   │   ├── data-observability.md   # Data Obs guide (freshness, quality, lineage)
│   │   └── business.md             # Business Observability guide
│   ├── integrations/
│   │   ├── aws.md                  # AWS services integration guide
│   │   ├── servicenow.md           # ServiceNow integration
│   │   └── alerting.md             # Alerting channels guide
│   └── runbooks/
│       ├── data-freshness-alert.md
│       └── pipeline-failure.md
├── src/
│   ├── collectors/                 # Custom OTEL receivers
│   │   ├── aws_glue_receiver/
│   │   ├── aws_lambda_receiver/
│   │   ├── aws_emr_receiver/
│   │   └── aws_rds_receiver/
│   ├── quality/                    # Data quality engine
│   │   ├── checks/
│   │   ├── freshness.py
│   │   ├── lineage.py
│   │   └── scheduler.py
│   ├── alerting/                   # Alert routing & integrations
│   │   ├── servicenow.py
│   │   ├── pagerduty.py
│   │   └── slack.py
│   └── api/                        # DataObs REST API
│       └── main.py
├── kibana/
│   ├── dashboards/                 # Kibana dashboard exports
│   └── alerts/                     # Kibana alert rules
├── terraform/                      # AWS infrastructure as code
│   ├── modules/
│   └── environments/
└── tests/
    ├── unit/
    └── integration/
```

---

## Integrations

### Cloud Platforms
| Platform | Services | Status |
|---|---|---|
| **AWS** | Lambda, EMR, Glue, Athena, RDS, S3, EC2, EKS, Kinesis | ✅ Supported |
| **GCP** | BigQuery, Dataflow, Cloud Functions, GKE | 🚧 In Progress |
| **Azure** | ADF, Synapse, AKS, Azure Functions | 🚧 In Progress |

### Alerting & ITSM
| System | Type | Status |
|---|---|---|
| **ServiceNow** | Incident, Problem, Change | ✅ Supported |
| **PagerDuty** | On-call, Escalation | ✅ Supported |
| **Slack** | Channel alerts, threads | ✅ Supported |
| **Email** | SMTP, SES | ✅ Supported |
| **Opsgenie** | Alert routing | 🚧 In Progress |

---

## Documentation

| Document | Description |
|---|---|
| [Architecture Overview](docs/architecture/overview.md) | System design and component interactions |
| [Four-Tower Model](docs/architecture/four-tower-model.md) | Detailed tower framework documentation |
| [AWS Integration Guide](docs/integrations/aws.md) | Complete AWS services setup |
| [Data Observability Guide](docs/towers/data-observability.md) | Freshness, quality, lineage setup |
| [ServiceNow Integration](docs/integrations/servicenow.md) | ITSM integration guide |
| [Alerting Setup](docs/integrations/alerting.md) | All alerting channels configuration |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions welcome.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
