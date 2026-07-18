# DataObs Productization — Master Execution Plan

## Mission

Transform `Jagadeeshck/DataObs` from a POC/starter repository into a production-grade, Elasticsearch-native observability product focused primarily on:

1. Data Observability
2. Data Pipeline and Job Observability
3. Data Streams Monitoring
4. End-to-end lineage and impact analysis
5. Automated incident response and remediation
6. Advanced, product-quality visualisation

The product must be comparable in user experience and core capability to Datadog Data Observability and Data Streams Monitoring, while using Elasticsearch and Kibana as the primary analytical, storage, search, alerting, automation, and investigation platform.

Do not treat Elasticsearch, OpenSearch, Grafana Cloud, and other backends as equal alternatives. Elasticsearch/Kibana is the mandatory primary platform. OpenTelemetry and OpenLineage remain the vendor-neutral ingestion standards. Optional exporters may remain as integrations, but they must not dilute or complicate the default product architecture.

Target Elastic Stack version: **9.4.2**.

---

## Non-negotiable engineering decisions

1. **Elasticsearch is the system of record and primary analytics platform.**
2. **Kibana remains the deep investigation and administration surface.**
3. **DataObs must provide its own polished standalone web application** for product workflows and advanced topology visualisation.
4. **OpenTelemetry is the default telemetry standard.**
5. **OpenLineage is the default lineage/job event standard.**
6. **Elastic Streams must be used for operational log onboarding, routing, parsing, schema, retention, failure-store visibility, and significant-event exploration.**
7. **Elastic Workflows must be used for automation and remediation where supported.**
8. Critical production automation must not depend only on technical-preview Streams workflow steps. Use stable Elasticsearch, ES|QL, HTTP, connector, alert, and Cases steps for critical actions. Put preview integrations behind feature flags.
9. All product APIs, indices, templates, data streams, saved objects, workflows, and UI routes must be tenant-aware.
10. No issue may be closed merely because source code contains the text `Resolves: #...`. Acceptance criteria and tests must be verified.

---

# Phase 0 — Mandatory open-issue closure gate

Complete this phase before starting productisation implementation.

At the time of this plan, the open issues are:

- #24 — Column distribution drift checks with dynamic thresholds
- #25 — End-to-end integration tests for API and alert delivery
- #28 — AWS Lambda OTel layer
- #29 — dbt integration
- #30 — Automated anomaly detection
- #31 — Multi-tenant Alloy configuration
- #32 — Grafana dashboard Terraform provisioning
- #46 — AI agents and autonomous remediation
- #47 — Azure observability
- #48 — GCP observability
- #49 — Snowflake observability
- #50 — Multi-cloud OpenLineage
- #51 — DataObs Advisor

## Required issue process

For every open issue:

1. Read the complete issue and acceptance criteria.
2. Locate all related implementation, tests, configuration, documentation, and CI coverage.
3. Create an acceptance matrix:
   - acceptance criterion
   - implementation file
   - test proving it
   - status: complete / partial / missing / superseded
4. Do not close partial issues.
5. Implement missing acceptance criteria for issues that are small or already substantially implemented.
6. For large roadmap issues that are being absorbed into the new product architecture:
   - migrate every requirement into the versioned product roadmap;
   - identify its destination pillar, milestone, API, UI, and integration package;
   - add a clear issue comment explaining that it is superseded by the product roadmap;
   - close it with `not_planned`, not `completed`;
   - preserve traceability in `docs/development/open-issue-closure-report.md`.
7. Close completed issues only after tests and CI pass.
8. Finish Phase 0 with:
   - zero open issues;
   - zero open cleanup PRs;
   - green CI;
   - `docs/development/open-issue-closure-report.md`;
   - a table linking every former issue to commits, tests, docs, and final disposition.

## Important checks already indicated by the repository

Do not assume these issues are complete:

- #24 has a drift implementation, but verify KL divergence, IQR/outlier ratio, rolling Elasticsearch baseline, alerting, configuration, and tests.
- #25 has integration-test scaffolding, but verify that the complete quality → OTel → Elasticsearch → API → Slack/PagerDuty/ServiceNow path runs in CI.
- #28 has an AWS Lambda README and decorator, but verify all examples, build script, context propagation, Terraform module, packaging, dashboard, and tests.
- #29–#32 also require full acceptance verification, not just the presence of a README or partial module.
- #50 has a strong OpenLineage foundation from PR #78, but the original issue includes cross-cloud integration and must be dispositioned honestly.

Create a dedicated branch and PR for Phase 0:

- Branch: `codex/issue-closure-sprint`
- PR title: `Complete and close the DataObs pre-productisation backlog`

Do not start Phase 1 until this PR is merged and all issues are closed.

---

# Phase 1 — Product identity and repository restructuring

Create a new branch from the updated `main` branch:

- Branch: `codex/dataobs-product-foundation`
- PR title: `Establish DataObs as an Elasticsearch-native product`

## Product identity

Use this positioning consistently:

> **DataObs is an Elasticsearch-native Data Observability and Data Streams Monitoring platform that shows how data moves, detects where reliability degrades, explains downstream impact, and automates safe remediation.**

Remove or rewrite language describing the main repository as:

- POC
- starter
- blueprint-only
- four-pillar-only
- dual-backend-first
- Grafana-first

POC/demo assets may remain, but isolate them under `examples/` or `demo/` and ensure they are not presented as the production runtime.

## Required repository boundaries

Refactor toward:

```text
DataObs/
├── services/
│   ├── api/
│   ├── quality-worker/
│   ├── topology-worker/
│   ├── workflow-sync/
│   └── integration-workers/
├── ui/
│   └── dataobs-console/
├── packages/
│   ├── domain-model/
│   ├── elastic-store/
│   ├── telemetry/
│   ├── lineage/
│   ├── pathways/
│   └── connectors/
├── config/
│   ├── elasticsearch/
│   ├── streams/
│   ├── workflows/
│   ├── kibana/
│   └── otel/
├── integrations/
├── infra/
├── helm/
├── tests/
├── examples/
└── docs/
```

Use an incremental migration. Preserve compatible imports and endpoints until replacement paths are tested.

## API production hardening

Migrate the production API incrementally to FastAPI while preserving existing route compatibility.

Required:

- application factory
- typed settings
- OpenAPI
- Pydantic request/response models
- tenant context
- RBAC hooks
- pagination/filtering/sorting
- request size and content-type validation
- consistent error model
- liveness and dependency-aware readiness
- Elasticsearch mandatory in production mode
- OTel tracing, metrics, and structured logs
- audit trail for mutations
- idempotency keys for ingestion endpoints
- optimistic concurrency for mutable configuration
- SSE endpoint for live topology/incident updates

---

# Phase 2 — Six-pillar product model

Replace the old four-pillar model in code, docs, API responses, tests, examples, dashboards, and UI.

## Pillar 1 — Platform Observability

**Question:** What is deployed, where, and is it healthy?

Coverage:

- hosts and VMs
- containers and Kubernetes
- serverless
- databases
- cloud data services
- platform versions, lifecycle, events, logs, metrics, and traces

Capabilities:

- infrastructure inventory
- runtime health
- dependency topology
- version/compliance status
- capacity and saturation
- platform incident correlation

## Pillar 2 — Data Pipeline Observability

**Question:** Are pipelines running correctly and on time?

Coverage:

- ETL/ELT
- Spark
- Airflow
- dbt
- Glue
- Lambda
- Kafka/Kinesis/SQS/RabbitMQ/PubSub
- dependencies, retries, schedules, throughput, latency, and SLAs

Capabilities:

- job health
- run comparison
- schedule/SLA monitoring
- retries and failures
- input/output record counts
- pipeline latency
- stream lag
- deployment change correlation

## Pillar 3 — Data Observability

**Question:** Can I trust my data?

Coverage:

- freshness
- volume
- schema
- nullness
- uniqueness
- cardinality
- distribution drift
- data contracts
- dataset and column lineage
- downstream consumers

Capabilities:

- asset catalog
- quality monitors
- historical baselines
- anomaly detection
- schema/change monitoring
- lineage and blast radius
- ownership and governance

## Pillar 4 — FinOps / Cost Observability

**Question:** What is the platform costing, and why?

Coverage:

- cloud and Elastic spend
- compute, storage, network, and query costs
- cost by tenant, team, pipeline, job, dataset, service, and environment
- idle and unused resources
- forecasts and anomalies

Capabilities:

- cost allocation
- unit economics
- budget/SLO correlation
- cost anomaly detection
- optimisation recommendations
- retention and storage forecasting

## Pillar 5 — Business Observability

**Question:** Is the platform delivering business value?

Coverage:

- adoption
- tenant usage
- SLA/SLO attainment
- critical business KPIs
- time-to-data availability
- incident impact

Capabilities:

- business KPI correlation
- tenant health
- executive scorecards
- business impact estimation
- data-product reliability
- service and data-product SLOs

## Pillar 6 — AI / Agent Observability

**Question:** Can AI and autonomous agents be trusted, controlled, and audited?

Coverage:

- model and agent calls
- prompts, tools, retrieval, reasoning steps, and outcomes
- token usage, latency, cost, errors, and retries
- evaluation quality
- hallucination/grounding indicators
- autonomous remediation actions
- human approval and rollback

Capabilities:

- LLM/agent traces
- evaluation and quality signals
- tool-call lineage
- prompt/model version correlation
- cost and latency
- policy guardrails
- action audit trail
- remediation verification

All six pillars must use OpenTelemetry where applicable and support enrichment from CMDB/catalog/ownership sources such as ServiceNow CMDB.

Update:

- `src/core/pillars.py`
- all pillar tests
- README
- architecture diagrams
- API schemas
- maturity scoring
- sample configuration
- dashboard navigation
- UI navigation
- all references to `four-tower` / `four-pillar`

Rename:

- `docs/architecture/four-tower-model.md`
- to `docs/architecture/six-pillar-product-model.md`

Keep a migration note so old links are not silently broken.

---

# Phase 3 — Elasticsearch storage and data model

Use different Elasticsearch storage patterns according to mutability.

## Mutable product state — versioned indices and aliases

Use normal versioned indices plus stable aliases for:

- assets/catalog
- owners and teams
- monitor definitions
- data contracts
- workflow metadata
- integration configuration
- pillar configuration
- saved views
- incident state

Example:

```text
dataobs-assets-v1
dataobs-assets-write
dataobs-assets-read
```

## Append-only operational data — data streams

Use data streams for:

- OpenLineage events
- job runs
- quality results
- pathway edge measurements
- broker/topic/queue metrics
- incidents and alert events
- workflow executions
- cost measurements
- business KPI measurements
- AI/agent traces and evaluations

Use ECS and OTel semantic conventions wherever possible.

Create component templates, index templates, ingest pipelines, data-stream lifecycle/ILM policies, failure stores, aliases, transforms, and migration commands.

Never create or alter mappings opportunistically from request handlers in production.

## Suggested logical datasets

```text
logs-dataobs.openlineage-<namespace>
traces-dataobs.jobs-<namespace>
metrics-dataobs.quality-<namespace>
metrics-dataobs.pathways-<namespace>
metrics-dataobs.brokers-<namespace>
logs-dataobs.incidents-<namespace>
logs-dataobs.workflow-runs-<namespace>
metrics-dataobs.cost-<namespace>
metrics-dataobs.business-<namespace>
traces-dataobs.ai-<namespace>
```

Add:

- schema version
- tenant ID
- environment
- source integration
- owner/team
- service/data-product identity
- trace/run/job IDs
- event timestamp and ingestion timestamp
- data classification
- correlation IDs

Use transforms/latest indices for current-state summaries and fast UI reads.

---

# Phase 4 — Elastic Streams integration

Elastic Streams and Datadog Data Streams Monitoring are different concepts.

- Elastic Streams is primarily the managed operational-log onboarding, processing, routing, schema, retention, failure-store, and significant-events capability.
- DataObs must build its own message-pathway monitoring layer for Kafka, Kinesis, SQS, RabbitMQ, Pub/Sub, and similar systems using Elasticsearch.

## Use Elastic Streams for

1. Raw operational logs from platforms, brokers, jobs, consumers, producers, and DataObs itself.
2. OTel-normalised ingestion through `logs.otel`.
3. ECS-preserving ingestion through `logs.ecs`.
4. Hierarchical routing into child streams by:
   - tenant
   - environment
   - cloud
   - platform
   - service
   - pipeline
   - integration
   - severity
5. Parsing and field extraction.
6. Redaction and PII/secret handling.
7. Enrichment using ownership, CMDB, deployment, and data-product metadata.
8. Per-stream retention and storage analysis.
9. Failure-store and degraded-document visibility.
10. Significant-event and knowledge-indicator exploration.

Do not manually modify Elasticsearch templates or pipelines marked as managed by Streams.

Add feature flags:

```text
DATAOBS_ELASTIC_STREAMS_ENABLED=true
DATAOBS_ELASTIC_STREAMS_SIGNIFICANT_EVENTS_ENABLED=false
DATAOBS_ELASTIC_STREAMS_WORKFLOW_STEPS_ENABLED=false
```

Enable preview/Enterprise-dependent features only when explicitly configured.

## DataObs Data Streams Monitoring semantic layer

Instrument producers and consumers with OTel messaging spans and W3C context propagation where supported.

Collect broker/queue state from native APIs and integrations.

Build a topology/pathway projection with one document per time-bucketed edge.

Required edge fields:

```text
tenant_id
environment
source_node
destination_node
source_type
destination_type
messaging_system
cluster
topic_or_queue
partition
consumer_group
pathway_id
parent_pathway_id
p50_latency_ms
p95_latency_ms
p99_latency_ms
throughput_messages_per_second
throughput_bytes_per_second
payload_size_p50_bytes
payload_size_p95_bytes
lag_messages
lag_seconds
error_rate
retry_rate
dlq_messages
last_seen
owner_team
business_service
estimated_cost
health_state
health_reasons
```

Implement:

- pathway discovery
- edge/full/internal latency
- throughput
- message lag
- retention-risk calculation
- poison-message and DLQ signals
- schema/config change overlays
- producer/consumer ownership
- root-cause candidates
- upstream/downstream blast radius
- pathway SLOs
- anomaly detection
- time-window comparison

---

# Phase 5 — Elastic Workflows integration

Elastic Workflows is the preferred automation engine for supported deployments.

## Workflow categories

Create version-controlled workflow YAML templates for:

### 1. High consumer lag

- alert trigger
- query pathway, topic, partition, and consumer-group context
- calculate retention risk
- determine upstream/downstream impact
- collect related logs/traces/infrastructure
- optionally scale consumer deployment
- create/update Elastic Case
- notify Slack/PagerDuty/ServiceNow
- wait and verify recovery
- record remediation outcome

### 2. Freshness breach

- identify stale asset
- traverse upstream lineage
- identify failed/delayed job
- rerun or backfill through connector/API
- rerun quality checks
- verify downstream recovery
- notify owner and consumers

### 3. Schema drift

- identify changed fields
- calculate downstream impact
- pause/quarantine unsafe processing
- require human approval for high-impact changes
- resume after validation
- document decision and rollback path

### 4. Job failure

- gather run details, stack trace, related logs, Spark stages, and infrastructure metrics
- compare against previous successful runs
- create incident/case
- rerun when policy permits
- verify outputs and data quality

### 5. Cost anomaly

- identify tenant, job, service, storage tier, or query causing cost increase
- correlate with deployments and volume
- notify owner
- optionally apply approved optimisation
- verify service/data SLO remains healthy

### 6. AI/agent quality failure

- identify prompt/model/tool version
- retrieve evaluation and grounding evidence
- disable or roll back unsafe version
- create case
- require approval for high-risk actions
- verify the replacement

## Workflow engineering rules

- Store templates under `config/workflows/`.
- Add a sync/validation command.
- Validate YAML and required connectors in CI.
- Persist workflow execution summaries in Elasticsearch for the DataObs UI.
- Support manual, scheduled, alert, and event-driven triggers.
- Use explicit concurrency keys and idempotency.
- Use `waitForInput` for high-risk human approval.
- Use stable Elasticsearch/ES|QL/HTTP/connector/Case actions for critical workflows.
- Put direct Streams action steps behind the preview feature flag.
- Add a global workflow-failure handler.

---

# Phase 6 — Advanced standalone DataObs console

Create `ui/dataobs-console` using:

- React
- TypeScript
- Vite
- Elastic EUI
- Elastic Charts
- Cytoscape.js or an equivalent scalable graph library
- Playwright
- generated API client from OpenAPI

Do not build only a collection of Kibana dashboards. Kibana remains available for deep investigation, but DataObs requires a coherent product experience.

## Required product screens

### 1. Command Center

- health across all six pillars
- open incidents
- failing pipelines
- stale/low-quality data
- stream lag and retention risk
- cost anomalies
- business impact
- AI/agent risk
- tenant and environment filters
- global time picker

### 2. Live Data Flow Map

Show:

- sources
- producers
- topics/queues
- jobs/transforms
- datasets/tables
- dashboards/models/apps
- consumers

Visual encoding:

- animated edges for live data movement
- edge width = throughput
- edge colour/state = health
- edge pulse = active incident
- node halo = anomaly severity
- badges for freshness, quality, lag, cost, ownership, and SLO
- collapsed groups by platform/domain/team
- zoom from enterprise map to partition/column detail

Interactions:

- upstream/downstream expansion
- blast-radius mode
- root-cause mode
- path comparison
- time travel
- before/after deployment comparison
- incident overlay
- cost overlay
- ownership overlay
- click-through to logs, traces, metrics, Kibana, cases, workflows, and source system

### 3. Pathway Explorer

- choose start and end nodes
- show complete and partial pathways
- p50/p95/p99 end-to-end latency
- lag and throughput
- bottleneck contribution
- path SLO
- compare two time windows
- create monitor
- execute approved workflow

### 4. Asset 360

- metadata
- owner
- tags
- schema
- quality history
- freshness
- usage
- lineage
- downstream dashboards/models
- incidents
- SLOs
- cost
- recent changes

### 5. Job and Run Explorer

- job list and health
- run history
- run comparison
- stage/task timeline
- flame graph
- logs/traces/infrastructure correlation
- resource and cost efficiency
- input/output lineage
- rerun/remediation action

### 6. Topic / Queue / Stream 360

- producer and consumer services
- partitions
- consumer groups
- lag
- throughput
- retention risk
- replication/availability
- schemas and schema changes
- sampled/redacted message inspection where explicitly permitted
- configuration change overlay
- owner/on-call/repository links

### 7. Incident and Automation Workbench

- alert timeline
- suspected root cause
- affected assets/services
- business impact
- workflow execution steps
- human approvals
- remediation results
- evidence and audit log

### 8. FinOps View

- cost by tenant/team/product/pipeline/job/dataset
- cost trend and forecast
- unit cost
- idle resources
- Elasticsearch storage/retention cost
- anomaly explanation
- optimisation recommendations

### 9. AI / Agent Observability View

- agent/model inventory
- traces and tool calls
- prompt/model versions
- quality/evaluation trends
- latency and token/cost metrics
- grounding evidence
- policy violations
- autonomous action audit

## UX requirements

- polished responsive layout
- dark and light themes
- keyboard accessible
- saved views
- shareable URLs
- multi-tenant RBAC
- empty/loading/error states
- virtualisation for large lists
- graph performance tests
- live updates using SSE
- deep links to Kibana rather than duplicating every investigation feature

---

# Phase 7 — Datadog-inspired capability parity

Implement the following product capability groups without copying Datadog branding, proprietary code, or exact UI.

## Data Catalog

- searchable asset inventory
- asset types and hierarchy
- owners, tags, descriptions, source links
- monitor status
- lineage summary
- health and usage
- saved searches/views

## Quality Monitoring

Table-level:

- freshness
- row count/volume
- custom query/ES|QL metric
- schema drift

Column-level:

- freshness
- nullness
- uniqueness
- cardinality
- percentage zero
- percentage negative
- min/max/mean/sum/stddev
- distribution drift
- configurable and learned baselines

## Jobs Monitoring

- health and reliability
- failed and long-running jobs
- run details
- stage/task analysis
- stack traces
- logs
- infrastructure
- input/output data
- run comparison
- cost and optimisation

## Lineage

- assets, jobs, dashboards, models, and applications
- dataset and column levels
- anchor-based exploration
- upstream root cause
- downstream blast radius
- change-impact preview
- ownership routing

## Data Streams Monitoring

- topology
- producer/consumer/queue relationships
- end-to-end and edge latency
- throughput
- lag
- retention risk
- schema/config changes
- related logs/traces/infrastructure
- workflow automation

---

# Phase 8 — Security, tenancy, governance, and licensing

Required:

- tenant ID on every product document
- namespace strategy
- Kibana spaces
- API RBAC
- least-privilege API keys
- document/field-level controls where licensed
- audit logs
- encryption and secret references
- PII redaction
- message inspection disabled by default
- explicit approval and audit for high-risk workflows
- retention by tenant and data class
- data residency metadata
- backup/restore
- schema migration/rollback
- feature/licence matrix

Document which capabilities require:

- Elastic Basic
- paid Elastic subscription
- Enterprise
- generative AI connector
- technical-preview feature flag

Core DataObs ingestion, catalog, lineage, quality, pathway calculations, and standalone UI must degrade gracefully when optional licensed features are disabled.

---

# Phase 9 — Testing and production gates

## Required test layers

- unit tests
- Elasticsearch-backed integration tests
- end-to-end signal-path tests
- OpenLineage compatibility tests
- OTel semantic-convention tests
- Streams configuration tests
- Workflow YAML validation tests
- API contract tests
- UI component tests
- Playwright end-to-end tests
- tenancy/isolation tests
- security tests
- upgrade/migration tests
- performance tests for graph and pathway queries
- failure/recovery tests
- Docker Compose smoke test
- Helm lint/render/install test
- Terraform fmt/validate/plan
- image vulnerability scans for all production images
- SBOM and dependency audit

## CI must block merge on

- failed tests
- invalid mappings/templates/pipelines
- invalid workflow YAML
- invalid OpenAPI
- lint/type failures
- critical vulnerabilities
- broken Helm/Terraform
- missing migration notes
- documentation link failures
- accessibility failures for critical UI paths

---

# Required documentation changes

Create or update:

```text
README.md
docs/product/vision.md
docs/product/product-positioning.md
docs/product/roadmap-v1.md
docs/product/feature-matrix.md
docs/architecture/six-pillar-product-model.md
docs/architecture/product-runtime.md
docs/architecture/elasticsearch-data-model.md
docs/architecture/elastic-streams.md
docs/architecture/elastic-workflows.md
docs/architecture/data-streams-monitoring.md
docs/architecture/visualisation-ux.md
docs/architecture/multi-tenancy.md
docs/architecture/licensing-and-feature-flags.md
docs/operations/production-readiness.md
docs/operations/upgrade-and-migration.md
docs/operations/backup-restore.md
docs/operations/workflow-safety.md
docs/development/open-issue-closure-report.md
docs/development/repository-structure.md
```

The README must clearly state:

- Elasticsearch/Kibana is the primary platform.
- OpenTelemetry/OpenLineage are ingestion standards.
- DataObs has six pillars.
- Elastic Streams and Workflows integration.
- a dedicated DataObs console exists.
- POC/demo assets are not production runtime.
- current production-readiness status is factual and not overstated.

---

# PR and delivery strategy

Do not create one unreviewable mega-PR.

Use this sequence:

1. `codex/issue-closure-sprint`
2. `codex/dataobs-product-foundation`
3. `codex/elasticsearch-streams-workflows`
4. `codex/data-streams-monitoring`
5. `codex/dataobs-console`
6. `codex/product-hardening-release`

For every PR include:

- scope
- architecture decisions
- files changed
- migrations
- test evidence
- screenshots for UI
- security/licensing impact
- rollback
- issues closed/superseded
- follow-up work

Leave each PR reviewable and green before merge.

---

# Definition of done for DataObs v1 product foundation

The foundation is complete only when:

- all previous open issues are closed with traceable disposition;
- the repository no longer presents itself as a POC/starter;
- Elasticsearch 9.4.2 is the mandatory production backend;
- the six-pillar model is implemented in code and docs;
- OpenTelemetry and OpenLineage ingestion is production hardened;
- the Elasticsearch data model is versioned and migration controlled;
- Elastic Streams is integrated for operational log routing/processing;
- Elastic Workflows templates are validated and usable;
- Data Streams Monitoring topology and pathway APIs exist;
- the standalone DataObs console provides Command Center, live flow map, Pathway Explorer, Asset 360, Job Explorer, Stream 360, Incident Workbench, FinOps, and AI/Agent views;
- all production gates are green;
- deployment, operations, security, licensing, and upgrade documentation is complete.

## Phase 0 collection-plane foundation addendum

Phase 0 adds the DataObs collection-plane architecture without changing the product direction above. The default collection hierarchy is: reuse Elastic Agent and existing Elastic integrations first; use Elastic Agent as EDOT Collector or standalone EDOT for OpenTelemetry-native telemetry second; build DataObs Scanner connectors only for metadata, schema, freshness, profiling, quality, query-history, and lineage capabilities not provided by reusable integrations or receivers. See `docs/architecture/dataobs-agent-and-collection-plane.md`, `docs/architecture/database-scanning-and-profiling.md`, and `docs/product/collection-capability-matrix.md`.
