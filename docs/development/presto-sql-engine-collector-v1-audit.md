# Presto SQL engine collector v1 audit

1. **Audited base:** `e99ff14c74f0df4e65818dadd539d17ae96b0317`.
2. **Terminal migration:** dynamically derived as `0028_pathway_investigation_history`.
3. **Registry:** AWS, Azure, BigQuery, Databricks, Snowflake, Trino; this change explicitly adds Presto.
4. **Foundation:** contracts, fixed registry, SQL validation, identifiers, bounded execution, pagination, normalization, metadata, and errors are reusable.
5. **Trino review:** provider, dialect, SQL, collectors, connection, evidence, tests, and workflow were reviewed; identities and protocol code remain separate.
6. **Existing Presto:** no provider existed.
7. **Reusable:** Integration SDK capabilities, generic observations/runs/checkpoints/OCC, SQL-engine safety and execution.
8. **Presto-specific:** configuration, Basic auth, official-client adapter, X-Presto source, dialect projections, normalization, errors, collectors, and evidence.
9. **Runtime:** CPython 3.14.4.
10. **Client:** official PyPI/GitHub current version 0.8.4 imports and constructs Basic auth on 3.14.4; complete DBAPI/live compatibility is pending the opt-in 0.298.1 test, so status is expected.
11. **Authentication:** Basic only, HTTPS and environment password reference required; Kerberos planned v2; JWT/OAuth/certificate deferred.
12. **Migration:** none. Generic strict provider observations, runs, status, checkpoint, and evidence metadata mappings suffice; released migrations are unchanged.
13. **Supported:** resource/metadata/metric collection, bounded runtime query evidence, schema discovery, health, incremental collection.
14. **Unsupported:** logs, lineage, costs, event-driven collection, arbitrary SQL, profiling, data quality, sampling, query text/user analytics/plans, complete history, materialized-view inventory.
15. **Privacy:** Presto projections were independently selected; no Trino materialized-view assumption, query REST API, SQL/user fields, or node/task topology.
16. **Exact target:** Presto 0.298.1, presto-python-client 0.8.4, CPython 3.14.4; hosted live evidence not yet retained.

Official-version verification on 2026-08-08 used the PrestoDB GitHub latest release API and PyPI project JSON: server 0.298.1 and client 0.8.4.
