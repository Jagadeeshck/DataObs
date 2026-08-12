# dbt intelligence architecture

The `integrations/dbt` package is the single untrusted-artifact boundary. It validates byte/depth/count limits and the artifact family/schema URI before producing immutable, bounded projections. `services/dbt_intelligence` orchestrates idempotency and project/resource projections. It never invokes dbt, reads profiles, or queries a warehouse.

Provider identity is dbt `unique_id`; canonical identity hashes tenant, environment, project, resource type and unique ID. Models, sources, seeds and snapshots map to canonical assets. Invocation IDs map to canonical run identity. Declared dependencies are emitted for canonical Lineage Intelligence with dbt provenance; runtime/OpenLineage evidence remains separate and reconciliation never deletes either edge.

Project health is the weighted mean of available components only. Missing evidence is returned in `missing_components`, reduces confidence, and can produce `partial` or `unknown`; it is never scored as zero or healthy.
