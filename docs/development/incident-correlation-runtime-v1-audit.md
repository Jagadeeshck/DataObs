# Incident correlation runtime v1 audit

## Audited baseline

* **Audited SHA:** `043a4e368d40f0fe04d8d48610b1af613985357b` (local `main` equivalent on 2026-08-01). The checkout has no `origin`, so `git fetch origin main` failed and remote freshness could not be independently established.
* **PRs inspected from their complete merge patches:** #187 (`43ec068`), #202 (`915dcd2`, including closure findings in `incident-workbench-v1-closure-audit.md`) and #209 (`51f4df4`). Later local merges #210–#212 were inspected; none productionised this runtime. #212 is the latest Team 5 Console integration; #211 contains Team 0 release/security work.
* **Terminal migration:** `0024_job_run_reliability_runtime`, reported by `python scripts/release/current_terminal_migration.py`. No migration is added or changed here.
* **Baseline:** the focused Team 3 command completed with 32 passed.

## Verified baseline capability and gaps

PR #209 supplied versioned deterministic scoring, bounded safe feature extraction for asset/resource/product/service/time, explainable non-causal decisions, event-time thresholds and replay-aware flood counting. It still derived pairwise group identity, mutated flood input, lacked a durable repository, bounded server-side candidates, ingestion wiring, reconciler, read API and Event Storm Console.

The verified ingestion path was normalize → durable finding reconciliation → exact/stale handling → stable incident create/OCC update → return. Stable incident identity is `deterministic_id("incident", [tenant_id, deduplication_key])`; runtime work does not change it or overwrite the legacy source `correlation_key`.

## Existing strict storage resources

Generated manifest inspection confirmed these released resources and mapped fields. All share strict base fields (`id`, `tenant_id`, `environment`, `created_at`, `updated_at`, `status`, `metadata`) plus the incident-automation fields used below.

| Resource | Runtime use | Exact mapped fields used |
|---|---|---|
| `dataobs-incidents-v1` | stable incident input | `tenant_id`, `environment`, `incident_state`, `severity`, `correlation_key`, `correlation_version`, `affected_assets`, `data_product_ids`, `business_services`, `occurrence_count`, observation timestamps |
| `dataobs-findings-v1` | accepted evidence | finding identity/type, monitor/rule/trace/resource/product fields and observation timestamps |
| `dataobs-incident-correlations-v1` | group projection | `correlation_id`, `correlation_key`, `correlation_version`, `incident_id`, `resource_ids`, `affected_assets`, `data_product_ids`, `business_services`, `severity`, `confidence`, `occurrence_count`, timestamps, `status`, bounded `correlation_explanation`, bounded `metadata` |
| `logs-dataobs.correlation_event-*` | decisions/deferred work | `@timestamp`, scope, correlation identifiers/version, incident/policy, status, confidence, `reason_code`, bounded explanation/metadata |
| `dataobs-incident-suppressions-v1` | flood projection | correlation identifiers/version, representative `incident_id`, bounded resource/topology samples, severity/count/timestamps/status, bounded metadata |
| `logs-dataobs.incident_suppression-*` | transitions and notification intent | timestamp, scope, correlation identifiers/version, incident, status, action/reason and bounded metadata |
| `dataobs-action-idempotency-v1` | audited but not reused | its operation-document contract is incompatible with claim/checkpoint semantics |
| `logs-dataobs.incident_merge_split-*` | audited, not used | reserved for human merge/split history; automatic group merge is a non-goal |

Aliases/templates are generated from the manifest: mutable resources have `-read`/`-write` aliases and append-only resources have their `logs-dataobs.*-*` templates. Existing mapped top-level fields support mandatory filters; supplementary bounded arrays live in `metadata`. A forward migration is therefore neither justified nor added.

## Resulting runtime, ownership and certification

The runtime adds strict bidirectional adapters, Elasticsearch OCC repositories, server-bounded candidate lookup (tenant/environment/state/version/evidence, 2 s timeout, 50 maximum, deterministic sort/source allowlist), stable singleton-born groups, append-only idempotent decisions, immutable flood evaluation, durable notification intent and bounded deferred reconciliation. Incident persistence remains committed on every downstream failure and the response says which phase is deferred.

Team 3 owns the service, API, incident Console, tests and capability docs. Shared changes are limited to API composition, method-aware permission classification, typed routes and the Team 3 API client. Team 0 still owns worker packaging and exact-commit certification; Team 5 owns global Console design.

Status remains **functional_unvalidated**. Local unit/API checks are not Elasticsearch 9.4.2, hosted Playwright/axe, retained `incident-correlation-runtime-v1-evidence`, or independent verification. Remaining gaps are a hosted exact-head run, retained mapping/alias/OCC/restart evidence, and Team 0 deployment of the documented worker command.
