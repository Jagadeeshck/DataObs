# DataObs API Store Layer

This document defines the persistence contract used by the FastAPI API layer and how each backend implements it.

## Unified contract

The API uses a single primary store interface (`StoreProtocol`) from `src/api/store.py`.

Required operations:

- Quality results: `save_quality_result`, `get_quality_result`, `list_quality_results`
- Rules: `save_rule`, `add_rule`, `get_rule`, `get_all_rules`, `get_rules_for_dataset`, `delete_rule`
- Lineage: `save_lineage_node`, `get_lineage_node`, `save_lineage_edge`, `get_all_nodes`, `get_all_edges`, `get_downstream_impact`

FastAPI routes in `src/api/app.py` depend on a single injected `StoreBundle.store` that follows this contract.

## Supported backends

## 1) Memory backend (`DATAOBS_STORE_BACKEND=memory`)

- Implemented by `InMemoryStore` in `src/api/store.py`.
- Default for local development.
- Process-local state only (data is lost on restart).
- Supports full rule, quality, and lineage operations.
- `get_downstream_impact` uses breadth-first search (BFS) over in-memory lineage edges.

## 2) Elasticsearch backend (`DATAOBS_STORE_BACKEND=elasticsearch`)

- Implemented by `ElasticsearchStore` in `src/api/es_store.py`.
- Durable backend for production.
- Uses per-tenant index naming:
  - `dataobs-quality-results-<tenant>`
  - `dataobs-rules-<tenant>`
  - `dataobs-lineage-<tenant>`
- Uses tenant filters in read queries to prevent accidental cross-tenant reads.
- Stores lineage nodes and edges in the same lineage index via `doc_type` (`node` or `edge`).

## Tenant isolation model

Tenant isolation is enforced in two layers:

1. **Index-level isolation** by tenant-specific index names.
2. **Query-level isolation** by always including `tenant_id` terms in read queries.

This double enforcement is intentionally defensive and helps preserve isolation when mappings or index aliases evolve.

## Lineage graph model

Lineage is represented as a directed graph:

- Node document fields include `node_id`, `type`, `attributes`.
- Edge document fields include `edge_id`, `source_node_id`, `target_node_id`.
- Downstream impact traversal starts from a `node_id` and returns reachable targets up to a configurable depth.

## Legacy compatibility notes

`RuleStore` and `LineageStore` in `src/api/store.py` are legacy compatibility adapters for earlier ES index layouts.

- They are kept to avoid breaking older call sites/tests during migration.
- New route and feature work should use the unified store contract only.
- Future deprecation can remove adapters after all call sites are migrated.

## Guidance for future features

All new API features (for example OpenLineage, Snowflake integration, Advisor, AI agents) should:

1. Depend only on the unified store contract.
2. Avoid direct backend conditionals inside routes.
3. Add methods to the contract first, then implement parity in both backends.
4. Add backend-parity tests for memory and Elasticsearch modes.
5. Preserve public endpoint response shapes for compatibility.
