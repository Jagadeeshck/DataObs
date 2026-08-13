# Team 4 SQL Server Database Collector v1

The `sqlserver` Integration SDK provider (version `1`) reuses `DatabaseIdentity`, `FixedStatementRegistry`, `BoundedStatementExecutor`, bounded generic observations, partial failures, and durable generic checkpoints. Provider-owned catalog statements inspect one configured database through `sys.schemas`, `sys.tables`, `sys.views`, `sys.columns`, `sys.types`, structural constraint/index views, and `sys.partitions`.

SQL Server 2025 (17.x) is primary and feature-detects vector column metadata; SQL Server 2022 (16.x) is secondary and uses a projection without vector fields. Tables expose safe temporal, ledger, memory-optimized, durability, and graph flags. Definitions, filter predicates, partition boundary values, workload SQL, identities, and business rows are excluded. `sys.partitions.rows` is labelled estimated. Optional `sys.dm_db_partition_stats` denial is a partial failure.

Supported SDK capabilities are resource, metadata and schema discovery, metrics, health, and incremental collection. Query history, Query Store, lineage, logs, cost, and events are unsupported. Team 4 emits source evidence only; Team 2 retains ownership of Data Quality, schema-change intelligence, contracts, canonical lineage, impact analysis, and CI gates.

Freshness and profiling are disabled by default. Explicit policies generate validated, bracket-quoted `MAX` and allowlisted aggregates only. **SQL Server SQL-free Query Performance Evidence v2** may consider numeric Query Store aggregates only after a separate privacy and security review.
