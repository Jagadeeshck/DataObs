---
inclusion: manual
---

# Elastic Enterprise Features — DataObs Integration Plan

> **Internal working document.** Maps Elastic Enterprise license capabilities to
> DataObs product pillars. Use this when designing features that leverage the
> Enterprise stack beyond the basic/open tier.

## License assumption

All features below assume an **Elastic Enterprise** subscription covering:
- Elasticsearch + Kibana Enterprise
- Machine Learning (X-Pack)
- Security (field/document-level, RBAC, OIDC)
- Watcher
- Cross-Cluster Search / Replication
- Transform API
- ESRE (Elasticsearch Relevance Engine)
- Fleet + Elastic Agent (included in Enterprise)
- APM Server (included in Enterprise)

The `xpack.license.self_generated.type: trial` used in local Docker stacks activates
all Enterprise features for 30 days. Production deployments require a valid license key
set via `POST /_license`.

---

## Feature map: Elastic Enterprise → DataObs pillars

### 1. X-Pack Machine Learning — closes our biggest gap

**What it gives us:**
- Unsupervised anomaly detection on any time-series metric without writing rules
- Forecasting on metric trends (volume, throughput, lag)
- Categorization jobs for log/event pattern detection
- `_ml/anomaly_detectors` API — create a job per monitor and ES runs detection natively

**DataObs integration:**
- Create an ML anomaly detector job for each active DataObs quality monitor that
  has baseline history (≥2 weeks of observations)
- Map ML anomaly scores → DataObs findings → existing incident pipeline
- Expose "auto-detect" toggle on monitor authoring UI — when on, creates an ES ML job
  instead of requiring manual threshold rules
- Store ML job IDs on the monitor document for lifecycle management

**Migration needed:** `0034_ml_anomaly_detector_jobs` — index to track ML job IDs per
monitor, per tenant.

**Files to update:**
- `src/quality/checks/` — add `ml_anomaly_check.py`
- `packages/elastic_store/` — new migration
- `src/api/monitor_routes.py` — `auto_detect` flag on monitor create/update
- `ui/dataobs-console/src/features/quality/` — auto-detect toggle in monitor authoring

---

### 2. Watcher — native alerting wired to incidents

**What it gives us:**
- `PUT /_watcher/watch/<id>` — ES-native watch definitions triggered on index queries
- Supports: threshold, compare, search conditions; HTTP, Slack, PagerDuty, email actions
- Runs inside ES — no external scheduler or polling loop

**DataObs integration:**
- When a DataObs monitor is activated, register a Watcher watch in ES that queries the
  quality observation index and fires when the evaluation result is `failing`
- Watcher fires → HTTP action to DataObs API `/internal/watcher/trigger` →
  existing finding → incident pipeline
- Replaces the current APScheduler poll loop for time-sensitive monitors
- Watcher watch IDs stored on monitor documents; lifecycle-managed with monitor CRUD

**Migration needed:** adds `watcher_watch_id` field to monitor index (additive, no
new migration required — field added via dynamic mapping or existing monitor migration).

**Files:**
- `src/quality/engine.py` — replace scheduler loop with Watcher registration
- `src/api/monitor_routes.py` — register/deregister watch on create/delete/enable/disable
- New internal route: `POST /internal/watcher/trigger` (auth: ES-internal only)

---

### 3. Transform API — continuous quality rollups without a scheduler

**What it gives us:**
- `PUT /_transform/<id>` — continuous pivot/latest transforms that aggregate source
  indices into summary indices
- Perfect for: freshness rollups (last-seen per asset), volume trends (daily row counts),
  schema change frequency

**DataObs integration:**
- Register a continuous transform per tenant that rolls up quality observations into
  an `dataobs-quality-summary-{tenant}` index
- Powers the Command Center overview tiles and asset health scores without
  re-aggregating on every API request
- Replaces expensive runtime aggregation queries with pre-computed summaries

**Migration:** `0034_quality_transform_summaries` — index template for summary indices.

---

### 4. Field-Level Security + Document-Level Security — storage-layer tenant isolation

**What it gives us:**
- `indices.field_security` and `indices.query` on Elasticsearch roles
- Tenant isolation enforced in ES itself, not only in the DataObs API
- Defense-in-depth: even if API authorization is bypassed, ES rejects cross-tenant reads

**DataObs integration:**
- Create one Elasticsearch role per tenant: `dataobs-tenant-{tenant_id}`
- Role restricts index access to `dataobs-*-{tenant_id}-*` pattern
- Role applied to the API service account used for that tenant's ES client
- Existing RBAC in `src/security/` remains the primary gate; ES FLS is the backstop

**Files:**
- `packages/elastic_store/` — role provisioning in migration or setup script
- `src/security/` — role lifecycle management

---

### 5. Cross-Cluster Search (CCS) — multi-environment observability

**What it gives us:**
- Query across multiple ES clusters in one search: `remote_cluster:index-pattern`
- No data replication required; queries fan out at search time

**DataObs integration:**
- Allow a DataObs instance to observe data assets across `dev`, `staging`, `prod`
  environments even when each runs its own ES cluster
- Watcher watches can also target CCS patterns
- Expose `environment` as a first-class filter in Command Center and Asset views
- Required configuration: CCS remote cluster registration (admin operation, not
  automated by DataObs)

---

### 6. ESRE (Elasticsearch Relevance Engine) — semantic asset catalog

**What it gives us:**
- Hybrid BM25 + dense vector search on any text field
- `semantic_text` field type — auto-embeds text at index time using Elastic's ELSER model
- Zero external embedding service required

**DataObs integration:**
- Add `semantic_text` field to asset documents for description and column names
- Asset search in Console becomes hybrid: keyword + semantic similarity
- "Find assets related to orders" returns assets by meaning, not just exact name match
- Migration: add `semantic_text` field to asset index mapping

---

### 7. Fleet + Elastic Agent — collector deployment

**What it gives us:**
- Centrally managed, auto-updating collector agents deployed via Fleet
- Built-in integrations: PostgreSQL, MySQL, Kafka metrics, AWS CloudWatch, etc.
- DataObs Scanner, Kafka Observer, and Monitor Runtime can be packaged as custom
  Elastic Agent integrations

**DataObs integration:**
- Package the DataObs Scanner Worker as a Fleet integration
- Package the DataObs Kafka Observer as a Fleet integration
- This replaces standalone Docker deployments with Fleet-managed agents for
  production environments
- Custom integration manifest: `integrations/elastic/fleet/`

---

### 8. APM Server — pipeline-to-data correlation

**What it gives us:**
- Traces, spans, and metrics from instrumented pipelines land in `traces-apm-*`
- DataObs already reads APM traces for pipeline job correlation (POC validated)
- APM service map shows which services write to which data assets

**DataObs integration:**
- Already implemented in POC — promote to production quality
- Link APM trace IDs to DataObs Job/Run records for end-to-end correlation
- Quality incident details page shows: "This finding occurred during Spark job
  `etl_orders_daily` — click to see the APM trace"

---

## Local development setup with Enterprise features

```bash
# Start the full stack with trial license (30-day Enterprise)
cp .env.example .env
# Set ELASTIC_PASSWORD and KIBANA_PASSWORD
docker compose up -d

# Verify Enterprise license is active
curl -s -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_license | python3 -m json.tool | grep '"type"'

# Enable ML (should already be enabled on trial)
curl -s -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_ml/info | python3 -m json.tool | grep '"enabled"'
```

For production, apply your license:
```bash
curl -X PUT -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_license \
  -H "Content-Type: application/json" \
  -d @elastic-license.json
```

---

## Docker Compose configuration for Enterprise features

The main `docker-compose.yml` already sets:
```yaml
xpack.license.self_generated.type: trial
```

For ML to work, ensure ES has enough memory (≥2GB JVM heap) and the ML node role:
```yaml
# In docker-compose.yml elasticsearch service:
environment:
  - xpack.ml.enabled=true
  - ES_JAVA_OPTS=-Xms2g -Xmx2g
  # node.roles defaults to all roles on single-node, including ml
```

The existing `docker-compose.yml` already sets `ES_JAVA_OPTS=-Xms2g -Xmx2g` ✅
