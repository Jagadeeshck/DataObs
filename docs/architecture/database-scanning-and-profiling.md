# Database Scanning and Profiling Design

The DataObs Scanner uses metadata-first, aggregate-only-by-default database access. Discovery uses `information_schema`, system catalogs, metadata APIs, and cloud control-plane APIs and must never use `SELECT *` for discovery.

## Metadata discovery

Connectors collect database/catalog, schema, table/view/materialized view, columns, native and normalized types, nullability, defaults, primary/foreign keys, unique constraints, indexes, partitions, comments, owner, creation/change timestamps where exposed, estimated row count, estimated storage, table statistics, and dependency metadata without reading business rows when possible.

## Schema monitoring

Each asset produces a canonical schema representation with normalized ordering and database-specific types. DataObs hashes the canonical form, compares it with the previous immutable snapshot, and emits explicit change events for column added, column removed, type changed, nullable changed, constraint changed, and partition changed. Downstream impact is calculated through lineage. The scanner emits OTel, OpenLineage, and DataObs events and stores immutable snapshots separately from latest asset state.

## Freshness

Freshness is policy driven per asset. Strategies include maximum timestamp column, source modification timestamp, ingestion/audit column, partition timestamp, query-history inference, and externally supplied watermark. DataObs never assumes every table uses the same timestamp column.

## Profiling and quality

Profiling defaults to aggregate-only queries and is opt-in per source or policy. Supported metrics include exact/estimated row count, null count/rate, distinct count/cardinality, uniqueness, min/max/mean/sum/stddev, percentage zero, percentage negative, string length distribution, category/top-value distribution, numeric histogram, freshness, distribution drift, and custom SQL assertions.

Safety controls include statement timeout, connection timeout, concurrency limit, rows/bytes scanned limit where supported, warehouse/cost limit where supported, sampling strategy, table and column allow/deny lists, PII classification, scan window, cancellation, retry policy, incremental checkpointing, query tagging/commenting, read-only transaction, resource group/warehouse selection, TLS verification, private CA bundles, and no raw data persistence by default. Raw samples are disabled by default and require explicit opt-in, redaction, size limits, audit events, and retention.

## State and scheduling

Default cadences are weekly full discovery, daily incremental discovery, 5-15 minute freshness checks for critical assets, daily profile scans, per-policy quality scans, hourly lineage/job scans where available, and daily query-history scans subject to privileges. State includes connector checkpoint, last successful run, last attempted run, schema fingerprint, per-asset cursor, lease owner, task version, and retry count. Task IDs are deterministic and result writes are idempotent.

## Credentials

Credential references support environment variables, Kubernetes Secrets, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, Vault-compatible systems, and local encrypted secret files for standalone development only. Passwords, tokens, password-bearing connection strings, and secrets must never be written into Elasticsearch documents, logs, traces, Git, or generated policy files.

## Least privilege examples

| Platform | Metadata-only | Aggregate profiling | Query history | Optional lineage |
|---|---|---|---|---|
| PostgreSQL | `CONNECT`, `USAGE` on schema, catalog visibility, `pg_read_all_stats` where approved | `SELECT` on approved tables/views or security-definer aggregate views | `pg_stat_statements` read role where installed | read definitions from `pg_depend`, views, procedures where allowed |
| MySQL | `SELECT` on `information_schema` and approved schemas | `SELECT` on approved tables/views | performance_schema access | routine/view metadata access |
| Microsoft SQL Server | `VIEW DEFINITION`, connect to database | `SELECT` on approved schemas/tables | `VIEW SERVER STATE` or Query Store read where approved | dependency DMVs and module definition access |
| Oracle | catalog dictionary access such as `SELECT_CATALOG_ROLE` subset or explicit views | `SELECT` on approved objects | AWR/ASH access where licensed and approved | dependency and PL/SQL metadata views |
