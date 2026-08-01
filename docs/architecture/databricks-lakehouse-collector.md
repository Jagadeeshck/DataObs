# Databricks Lakehouse collector

The explicitly registered generation `1` provider creates one isolated official SDK workspace client per collection run.
The trusted SDK context supplies tenant/environment/integration identity; configured workspace ID is an additional resource
boundary. HTTPS workspace hosts are matched to cloud-specific official patterns and only a SHA-256 fingerprint is emitted.

Read collectors use explicit SDK services, bounded token pagination, deterministic deduplication, safe field allowlists,
and family-level partial failures. Jobs/runs remain provider-native evidence for future Team 2 projection. Fixed parameterized
queries are limited to `system.query.history` (Public Preview) and `system.compute.warehouse_events`; they use INLINE
JSON_ARRAY results, workspace/time filters, ordering, row/byte bounds and cancellation. Query text, users, errors, paths,
locations, connection data, and external links are excluded.

Generic migration 0022 persistence writes observations before OCC checkpoint advancement. Evidence families are independently
identified as Unity Catalog, warehouses, jobs, job runs, query history, and warehouse events. Hosted exact-commit proof is
absent, so status is **functional_unvalidated**, not production ready or complete coverage.
