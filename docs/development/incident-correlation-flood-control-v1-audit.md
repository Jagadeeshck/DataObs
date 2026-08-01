# Incident correlation and flood control v1 audit

## Preflight record

* **Audited local main-equivalent SHA:** `5bd728f89efb49cea2e1c5d70640c1245761d7dc` (2026-08-01). Fetching GitHub `main` and inspecting PRs #187/#202 and later reviews was attempted, but this environment had no repository credentials (`fatal: could not read Username`) and web search returned HTTP 401. Therefore remote freshness and review certification remain limitations.
* **Terminal migration:** `0023_stream_pathway_reliability_runtime`, unchanged by this work.
* **Focused baseline:** 28 Team 3 tests passed before modification.

## Existing flow and implementation

Normalization creates a deterministic finding, the repository persists/reconciles it, deduplication finds a stable incident, and OCC merge increments only a genuinely new occurrence. Exact and stale replay return honest statuses. The former correlator produced only a deterministic key; it did not create explainable groups or durable flood state.

## Storage and mappings

Released resources verified in `packages/elastic_store/manifest.py` are `dataobs-findings-v1`, `dataobs-incidents-v1`, `dataobs-incident-correlations-v1`, `dataobs-action-idempotency-v1`, `logs-dataobs.correlation_event-*`, `dataobs-incident-suppressions-v1`, `logs-dataobs.incident_suppression-*`, and `logs-dataobs.incident_merge_split-*`, with generated read/write aliases for mutable indices. Incident mappings include `affected_assets` as keyword plus bounded flattened correlation fields. The correlation resource uses the shared strict incident-automation mapping and does not map every proposed first-class group field; compatible envelopes must use mapped fields/flattened metadata until a separately reviewed forward migration exists.

## Console and Phase 0

Current Console routes are `/api/v1/incident-workbench`, detail, timeline, mutations, and action preview. Phase 0 now catches `CursorMismatch` on timeline as bounded HTTP 400; production asset filtering uses an exact `affected_assets` term while free text remains restricted to title/impact summary; and the capability client supplies an ephemeral operation-scoped idempotency key, reuses it on retry, changes it with payload/scope, and disables rapid duplicate clicks.

## Ownership, gaps and migration decision

Team 3 owns `services/incident_manager`, incident API routes/tests, incident Console features/API, and these documents. The only unavoidable shared change is the transport's optional header argument; released migrations, security internals, deployment and capability ledger are untouched. No migration was added and no released migration was modified. Production gaps remain: durable correlation/flood repository wiring, dedicated read APIs, full Console storm inventory, notifier confirmation, deferred-worker deployment, and real Elasticsearch 9.4.2 certification. The v1 pure engine is safe to integrate incrementally without changing stable incident identity.
