# Team 4 MariaDB database collector v1

MariaDB is a first-class `mariadb` provider, not a MySQL alias. It reuses the engine-neutral database identity, fixed-statement executor, observation, fingerprint, checkpoint, freshness, and aggregate-profiling contracts. All catalog statements, product detection, type/engine normalisation, TLS connection construction, and evidence filtering are MariaDB-owned.

Version 1 supports resource, metadata and schema discovery, metrics, health, and incremental collection. Query history, lineage, logs, cost, and event-driven collection are unsupported. Team 4 emits source evidence; Team 2 owns quality, change intelligence, lineage, contracts, impact, and gates.

Catalog collection is bounded and structural: schemas, relations/views, safe columns, constraints/FKs/CHECK presence, indexes, and partitions. `SEQUENCE` and `SYSTEM VERSIONED` table types are retained as safe categories; historical rows and sequence values are never read. User-statistics and Performance Schema are optional and are not queried.
