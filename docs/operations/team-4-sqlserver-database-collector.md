# Operating the Team 4 SQL Server collector

Install `requirements-sqlserver.txt` on a Python 3.10+ worker and configure a secret reference. A missing optional driver returns `dependency_unavailable` without affecting other providers. The factory disables process-global `mssql-python` pooling before connecting, uses `autocommit=True`, bounds connection/query/run/results, never shares connections across threads, and closes connections and cursors.

Use `strict` TLS for SQL Server 2022+ (`Encrypt=Strict`, TDS 8.0). The structured `mandatory` fallback always sets `Encrypt=Mandatory;TrustServerCertificate=no`. Optional `hostname_in_certificate` supports an approved DNS alias. Optional encryption, certificate bypass, DSNs, arbitrary connection options and connection strings are rejected.

Scopes are `identity`, `schemas`, `relations`, `columns`, `constraints`, `indexes`, `partitions`, `schema_snapshot`, optional `storage_statistics`, and configured `freshness/<relation>` / `profiling/<relation>`. Collection follows collect → normalize → redact → persist → OCC checkpoint advance. A failed scope does not advance; successful siblings remain valid. Low-cardinality telemetry must use only provider, capability, evidence family, status, stable error, and resource type labels.

Live contracts are opt-in with `RUN_SQLSERVER_INTEGRATION_TESTS=1` and separate synthetic SQL Server 17/16 hosts. This v1 is `functional_unvalidated`, not production ready or certified. It does not certify Azure SQL Database, Azure SQL Managed Instance, or Synapse.
