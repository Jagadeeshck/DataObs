# Data Contracts and Schema Governance v1 preflight

- **Audited main:** `ee8bb0363df503e60c85136f6d46ecb6ce606633` (repository had no configured remote; fetch was attempted and could not run).
- **Terminal migration before work:** `0026_stream_anomaly_retention_intelligence`; decision: add append-only `0027_data_contracts_schema_governance`, never modify a released migration.
- **Recent Team 2 merge:** PR #223, lineage impact/change intelligence (`b231b18`, implementation `b574bd4`). Main also contains PRs #219–#224.
- **Canonical identity/schema:** canonical `asset_id` and platform identity in `packages/domain_model`; current schema in `dataobs-schema-current-v1`, immutable snapshots/changes in `logs-dataobs.schema_snapshot-*` and `logs-dataobs.schema_change-*`.
- **Quality:** `services/monitoring` owns monitor contracts and `services/monitor_runtime` owns evaluation; contracts reference monitor IDs rather than execute checks.
- **Lineage:** `services/lineage_intelligence/impact.py` supplies bounded impact analysis over the existing graph.
- **Data products/ownership:** contracts retain canonical product IDs and asset ownership; membership and ownership remain in their existing domains.
- **Permissions:** assets, lineage, quality, monitors and data-products use narrow read/write vocabulary; contract APIs must be deny-by-default when wired.
- **Console routes:** `ui/dataobs-console/src/app/routes.ts` is authoritative and lazy-loaded; `App.tsx` is not edited.
- **Elasticsearch conventions:** mutable projections use strict explicit mappings and seq_no/primary_term OCC; evidence streams are append-only using create semantics and ILM.
- **ETag/cursors/idempotency/audit:** repository OCC maps revision to ETag; the Data Product HMAC cursor binds tenant/environment/resource/filters and expires; lifecycle events follow immutable audit patterns and idempotency scope includes operation plus request fingerprint.
- **Certification:** capability workflows use exact-commit manifests and independent verification. Hosted evidence is not available locally.
- **In scope:** typed contracts and immutable versions, lifecycle validation, deterministic schema/quality/freshness/volume/metadata evaluation, durable mappings/repository boundary, tenant isolation, accessible initial Console routes/views, tests and architecture/operations/security docs.
- **Excluded:** write/pipeline blocking, provider mutation, arbitrary code/SQL, raw rows, duplicate monitor/runtime/lineage/product/incident systems, destructive remediation, and production-readiness claims.
