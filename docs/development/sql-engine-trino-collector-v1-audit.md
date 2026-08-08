# SQL engine / Trino collector v1 audit

* Audited base SHA: `70f77d85b17776fe2222d591788f145269479057`.
* Dynamically derived terminal migration: `0027_platform_environment_tenant_multicluster_lifecycle` (`scripts/release/current_terminal_migration.py`). Release metadata currently reports a pre-existing certification-manifest mismatch; the 27 released migrations passed immutability and registry tests.
* Registry before change: AWS, Snowflake, Databricks, BigQuery, Azure. After change: those five plus explicit Trino.
* Scanner architecture: `packages/agent_sdk` and `services/scanner_worker` are the legacy Scanner Worker. `integrations/databases/postgres` uses it for discovery, privileges, freshness, profiling, and lineage. It is deliberately unchanged and not dual-registered.
* Reused Integration SDK production code: capabilities, trusted context, observations, partial failures, explicit registry, generic Collection Manager persistence/checkpoint/OCC resources. Strict generic mappings represent Trino evidence, so no migration was added.
* Not reused: legacy PostgreSQL execution/profiling, Team 2 lineage/quality paths, demos/POCs and test utilities. Profiling is unsafe for heterogeneous Trino connectors.
* Search audit found existing roadmap documentation for Trino/Presto but no production Trino provider. References to DBAPI/information schema in warehouse/database implementations were patterns, not a reusable arbitrary SQL layer. Presto remains not implemented.
* Decision: an internal, non-configurable SQL-engine package owns identifiers, fixed statement validation, bounded `fetchmany`, cancellation and contracts. Trino supplies a closed dialect/registry and isolated official-client connections.
* Dependency: project-maintained `trino>=0.338,<0.339`, tested locally at import/unit level with 0.338.0; optional and lazy. Server 483 is the v1 compatibility target but remains expected, not certified, until the live workflow runs.
* Security boundary: verified HTTPS, structured endpoints, secret references, deterministic source, no impersonation/headers/roles/session properties, no SQL/user/node locations, no business rows, and no arbitrary SQL. Direct protocol only.
* Supported: discovery, metadata, metrics, bounded runtime query evidence, schema, health and incremental collection. Unsupported: logs, lineage, costs, events, Presto, JDBC, OAuth browser flow, Kerberos, spooling, profiling, quality/custom SQL, sampling and complete history.

## Classification

| Area | Classification |
|---|---|
| `packages/collectors/sdk`, Collection Manager generic repositories/checkpoints | reusable Integration SDK production code |
| `packages/agent_sdk`, Scanner Worker, PostgreSQL integration | legacy Scanner Worker code |
| lineage and data-quality implementations | Team 2-owned code; not reused |
| fakes/fixtures under tests | test utility |
| demos/examples | POC/demo |
| generic Trino/Presto roadmap row | obsolete as a combined implementation claim; split into Trino functional_unvalidated and Presto planned |
