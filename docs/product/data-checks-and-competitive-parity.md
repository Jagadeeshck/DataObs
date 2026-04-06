# DataObs Data Checks and Competitive Parity Blueprint

This blueprint defines how DataObs performs data checks and how to cover feature categories commonly seen in modern data observability platforms.

## Core data check families (must-have)

1. **Freshness checks**
   - SLA-based staleness checks per table/topic
   - Late partition detection
   - Backfill-aware freshness policies

2. **Volume and distribution checks**
   - Row count thresholds and anomaly checks
   - Seasonality-aware volume baselines
   - Distinct count and cardinality drift

3. **Schema and contract checks**
   - Schema change detection (add/remove/type changes)
   - Contract enforcement for required fields, type compatibility, and constraints

4. **Field-level quality checks**
   - Null rate, uniqueness, value range, pattern format
   - Referential integrity checks
   - Aggregation checks (sum, avg, min/max sanity)

5. **Lineage-aware checks**
   - Upstream/downstream impact analysis
   - Blast-radius scoring for incident prioritization

6. **Business impact checks**
   - KPI guardrails tied to datasets and pipelines
   - Revenue/operational impact tags per incident

## DataObs check execution model

### 1) Rule definition
- Rules are declared per dataset in config or API.
- Each rule contains severity, threshold, schedule, and owner metadata.

### 2) Rule execution
- Quality engine runs checks on schedule.
- Each check returns: status, metric_value, threshold, details, and message.

### 3) Baselines and anomaly detection
- Historical results in Elasticsearch establish baseline behavior.
- Elasticsearch native ML jobs detect drift/spikes for freshness/volume metrics.

### 4) Incident workflow
- Failures are routed to Alert Manager.
- Routing policies fan out to ServiceNow, PagerDuty, Slack, or email.
- Lineage impact enriches incidents with affected downstream assets.

## Competitive parity roadmap (free/open)

### Phase 1: Foundation
- Freshness, row count, null, uniqueness, range, referential integrity
- Schema drift and baseline storage
- Rule management API and lineage API

### Phase 2: Advanced detection
- Dynamic thresholds and seasonality-aware anomalies
- Column-level distribution drift (quantiles/histograms)
- Incident grouping and deduplication

### Phase 3: Enterprise analytics
- End-user impact scoring and SLA compliance views
- Contract lifecycle (draft/approve/enforce)
- Root-cause assistant and recommendation engine

### Phase 4: Marketplace/integration
- Connectors for Airflow, dbt, Spark, Snowflake, BigQuery, Databricks
- Bidirectional sync with ITSM/ticketing and collaboration tools
- Reusable check templates by industry/domain

## Consultancy model enablement

For consulting projects, DataObs can be deployed as:
- single-tenant managed deployment per client
- shared control plane with tenant-level index separation
- reusable domain packs (finance, retail, healthcare) with prebuilt checks

This enables a fully free/open core while monetizing implementation, onboarding, and managed operations.
