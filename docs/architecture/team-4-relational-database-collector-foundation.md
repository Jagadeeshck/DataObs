# Relational Database Collector Foundation v1

`integrations/database` is the engine-neutral database layer; `integrations/sql_engine` remains for Trino/Presto. It defines collision-resistant identity, strict identifiers, provider-owned fixed statement registries, mutation rejection, bounded execution with rollback, structural evidence fingerprints, redacted errors and partial failures. It deliberately has no arbitrary SQL or row-sampling API. Provider adapters own dialect SQL and connections. PostgreSQL, MySQL, MariaDB, and SQL Server reuse this seam; SQL Server dialect/catalog/authentication logic remains provider-owned rather than using SQL-engine or JDBC infrastructure.

Collection scopes are database identity, relations, columns, constraints, indexes, partitions, snapshots, and configured per-relation freshness/profiling. Generic Team 4 persistence must complete before OCC checkpoint advancement; a failed scope does not advance and does not discard successful siblings. Evidence is deterministic and excludes secrets, raw SQL expressions, owners/comments and timestamps from fingerprints.

MySQL is the second adapter on this foundation. Its v1 provider reuses these contracts directly, including generic provider persistence and checkpoints, while keeping dialect SQL, TLS connection options, product detection, safe type normalization, and policy-owned aggregates provider-local.

## MariaDB implementation

The first-class `mariadb` v1 provider reuses this foundation while retaining MariaDB product detection, catalogs, normalisation, and connection policy in `integrations/databases/mariadb`.
