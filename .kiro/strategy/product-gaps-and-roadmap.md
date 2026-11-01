---
inclusion: manual
---

# DataObs — Product Gaps and Development Roadmap

> **Internal working document.** Tracks what we need to build to close the gap between
> the current `functional_unvalidated` state and a production-quality v1.0.0 and beyond.
> Updated: 2026-10-31.

## Current state (capability ledger summary)

| State | Count |
|---|---|
| foundation | 12 |
| functional_unvalidated | 37 |
| not_started | 6 |
| scaffold / optional | 2 |
| **Total** | **57** |

Zero capabilities are in `validated` state. Every capability needs hosted exact-SHA
evidence before it can count toward a release.

---

## Layer A — First release gate (v1.0.0, week of 2–6 Nov 2026)

These are the minimum viable capabilities that must be **hosted-certified** to ship v1.0.0.
Everything else may ship as `experimental`.

### A1. Shared platform (Team 0)
- [ ] Migrations `0001`–`0033` pass immutability check on release SHA
- [ ] Clean install: migrations apply, API starts, Console loads
- [ ] OIDC/JWKS authentication works end-to-end (Keycloak fixture)
- [ ] Tenant A cannot read Tenant B data (hosted proof)
- [ ] Backup snapshot + destructive restore + re-verify
- [ ] Helm lint + Kind smoke: install → upgrade → rollback
- [ ] SBOM (CycloneDX), provenance (SLSA), image signatures generated and verified
- [ ] `beta-security-hardening.yml` workflow passes

### A2. Streams and Pathways (Team 1)
- [ ] Kafka cluster inventory, topic list, consumer-group offsets hosted with real Kafka
- [ ] Pathway assembly and SLO evaluation hosted
- [ ] Stream 360 Console: Topic 360, Consumer Group 360, Cluster 360 — Playwright + axe pass
- [ ] Schema compatibility and connector 360 hosted

### A3. Quality, Jobs, Lineage (Team 2)
- [ ] Quality monitor CRUD, schedule, evaluate, find, incident — full hosted signal path
- [ ] OpenLineage job/run/lineage ingestion — hosted with real fixture
- [ ] Data Quality Console: monitor authoring, Monitor 360, findings — Playwright + axe pass
- [ ] Jobs/Run Console: inventory + 360 — Playwright + axe pass

### A4. Incidents (Team 3)
- [ ] OCC, dedup, append-only, notification delivery outcomes — hosted proof
- [ ] Incident Inbox and Workbench — Playwright + axe pass

### A5. Console (Team 5)
- [ ] Production build clean: typecheck, lint, prettier, vitest
- [ ] Bundle ≤ 1MB initial JS (bundle-check passes)
- [ ] All release-critical journeys (v1.0.0) — Playwright + axe, zero serious/critical violations

---

## Layer B — Immediate post-v1.0.0 (Q4 2026)

### B1. Elastic ML anomaly detection on quality monitors
**Why it matters:** closes the biggest product gap vs enterprise SaaS observability tools.
Auto-detect anomalies without writing rules — ML job per monitor on ES.

**Implementation plan:**
1. New migration `0034_ml_anomaly_detector_jobs`: index to track ML job IDs per monitor/tenant
2. `src/quality/checks/ml_anomaly_check.py`: create/start/stop ML anomaly detector jobs
3. `packages/elastic_store/migrations/0034_*.py`: migration definition
4. `src/api/monitor_routes.py`: `auto_detect: bool` flag on monitor create/update
5. `ui/dataobs-console/src/features/quality/MonitorForm.tsx`: auto-detect toggle
6. Map ML anomaly score → finding severity → existing incident pipeline
7. Certification: hosted ES with ML enabled, anomaly detected from synthetic data series

**ES API used:** `PUT /_ml/anomaly_detectors/<id>`, `POST /_ml/anomaly_detectors/<id>/_open`
**License:** Elastic Enterprise (X-Pack ML)

### B2. Watcher-driven alerting (replace APScheduler poll)
**Why it matters:** Watcher runs inside ES — no external scheduler, sub-minute latency,
survives API restarts. Native integration between quality findings and ES alerting.

**Implementation plan:**
1. `src/api/monitor_routes.py`: register Watcher watch on monitor activate
2. `src/quality/engine.py`: deregister Watcher watch on monitor deactivate/delete
3. New internal route: `POST /internal/watcher/trigger` (ES-to-DataObs webhook)
4. Watch definition: query quality observation index, fire on `failing` evaluation result
5. Fallback: APScheduler remains for environments without Enterprise license

**ES API used:** `PUT /_watcher/watch/<id>`, `DELETE /_watcher/watch/<id>`
**License:** Elastic Enterprise (Watcher)

### B3. Built-in quality check templates
**Why it matters:** teams shouldn't need to write SQL for the five standard dimensions.

**Templates to ship:**
- `freshness` — max age of most-recent record in a table/stream
- `row_count` — daily/hourly volume with Z-score threshold or ML job
- `null_rate` — fraction of nulls in key columns
- `schema_drift` — detect added/removed/renamed columns since last snapshot
- `uniqueness` — duplicate ratio on primary-key columns
- `distribution_shift` — histogram bucket drift on numeric columns (ES ML or IQR)

**Implementation:** extend `src/quality/checks/` with one class per template.
Each template generates the ES query or ML job configuration. Monitor authoring UI
shows template picker before custom SQL.

### B4. Asset catalog / discovery (ES full-text + ESRE)
**Why it matters:** teams need to find assets by name, description, owner, tag — not
just navigate to them. Elasticsearch makes this near-free to build.

**Implementation plan:**
1. Add `semantic_text` mapping to asset index (migration `0035_asset_semantic_search`)
2. `GET /assets/search?q=...` — hybrid BM25 + ESRE search across asset names,
   descriptions, column names, tags
3. Console: global search bar + asset catalog browse with facets (owner, type, status,
   data product membership)
4. Requires: ELSER model downloaded to ES (one-time `POST /_ml/trained_models/.../_deploy`)

### B5. dbt artifact ingestion
**Why it matters:** the largest segment of the data engineering market uses dbt.
Ingesting dbt artifacts (manifest.json, run_results.json) gives us asset lineage,
model health, and test results without any custom instrumentation.

**Implementation plan:**
1. `integrations/dbt/artifact_ingester.py`: parse dbt manifest + run_results
2. Map dbt models → DataObs Assets, dbt tests → DataObs quality findings
3. Emit as OpenLineage events through the existing OpenLineage ingestion pipeline
4. New CLI: `dataobs dbt ingest --manifest manifest.json --run-results run_results.json`
5. GitHub Action helper for CI/CD integration

---

## Layer C — Q1 2027 — Enterprise hardening

### C1. Field-level security + document-level security
Apply Elasticsearch FLS/DLS as defense-in-depth tenant isolation below the API layer.
Each tenant gets a scoped ES role. Migration provisions roles.

### C2. Cross-cluster search for multi-environment observability
Register remote ES clusters (dev/staging/prod) and enable CCS queries in DataObs.
Command Center becomes a true multi-environment view.

### C3. Transform API for quality summaries
Replace runtime aggregation queries on Command Center with continuous ES Transforms.
Pre-computed asset health scores, environment summaries, and SLO burn rates.

### C4. Fleet integration packaging
Package Scanner Worker and Kafka Observer as Fleet custom integrations.
Enables centrally-managed, auto-updating collector deployments at scale.

### C5. Additional quality source connectors
Extend Integration SDK providers using existing framework:
- Snowflake (warehouse-level quality scanning)
- BigQuery (dataset-level)
- Redshift (cluster-level)
- MySQL / MariaDB (already in requirements, needs certification)

Each provider: discovery → observation → quality findings → existing incident path.

---

## Layer D — Q2 2027 — Differentiating pillars

- **FinOps**: pipeline cost attribution via CloudWatch/BigQuery billing APIs → ES
- **Business reliability scorecards**: SLOs across data products consumed by business domains
- **AI/Agent observability**: trace LLM-backed pipelines via OTLP, surface data quality
  issues in RAG pipelines
- **DataObs Advisor**: ES ML + LLM-assisted root-cause suggestions on incidents

---

## Migration registry plan

| ID | Name | Layer | Status |
|---|---|---|---|
| 0001–0033 | Existing released migrations | A | immutable |
| 0034 | `ml_anomaly_detector_jobs` | B1 | planned |
| 0035 | `quality_transform_summaries` | B2 | planned |
| 0036 | `asset_semantic_search` | B4 | planned |
| 0037 | `tenant_es_roles` | C1 | planned |
| 0038+ | Provider-specific | C5 | TBD |

All new migrations are additive. No existing migration is ever edited.
