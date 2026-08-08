# Presto SQL engine collector v1

PrestoDB is an independent `presto` provider, not an alias for Trino. It is a thin dialect over `integrations/sql_engine`: fixed statements, identifier quoting, bounded `fetchmany`, cancellation, normalization, and safe failures remain shared.

The v1 target is Presto 0.298.1 with `presto-python-client` 0.8.4. Runtime identity uses `version()` and reports tested only for that exact pair; other versions are expected, unsupported, or unknown rather than silently certified. The repository runtime is Python 3.14.4. Import and authentication construction pass; a live DBAPI lifecycle against 0.298.1 remains opt-in and therefore compatibility is `expected`, not `tested`.

| Presto server | Python client | Python runtime | Status |
|---|---|---|---|
| 0.298.1 | 0.8.4 | 3.14.4 | expected; live gate pending |

Fixed reads cover `system.metadata.catalogs`, catalog `information_schema`, and aggregate projections from `system.runtime.nodes`, `queries`, and `tasks`. Query text, users, source, node locations, and task topology are omitted at SELECT time or defensively removed. `source` appears only in the DataObs self-filter predicate.

Runtime query evidence is `bounded_runtime_history`, never complete history. Restart, eviction, delay, access restriction, failover, or identity change may produce a coverage gap. Stable reasons are `coordinator_restart_possible`, `runtime_history_evicted`, `history_window_unavailable`, `access_restricted`, `server_identity_changed`, and `unknown_gap`.

Materialized-view inventory is unsupported: Presto v1 does not query Trino's metadata table or definitions. REST `/v1/query` APIs, profiling, data quality, sampling, custom SQL, plans, lineage, costs, and user analytics are also unsupported.
