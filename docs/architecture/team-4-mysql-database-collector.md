# Team 4 MySQL Database Collector v1

Status: **functional_unvalidated**. `MySqlDatabaseProvider` is provider type `mysql`, version `1`, and reuses the Integration SDK and relational database foundation for identity, fixed statements, bounded execution, safe observations, deterministic fingerprints, partial failures, persistence, and OCC checkpoints. It does not create a parallel framework or write Team 2 storage.

Discovery uses explicit projections from `information_schema.schemata`, `tables`, `columns`, `table_constraints`, `key_column_usage`, `referential_constraints`, `check_constraints`, `statistics`, and `partitions`. View definitions, defaults, generated/CHECK/functional-index/partition expressions, comments, query text, and raw business rows are excluded at selection or evidence sanitisation. Relation counts are labelled estimated. Partitions and every other family are bounded independently.

The supported capabilities are resource, metadata and schema discovery, metrics, health, and incremental collection. Query history, lineage, logs, cost, and event-driven collection are unsupported. Performance Schema is not read. A future **MySQL SQL-free Query Performance Evidence v2** may define bounded text-free evidence; v1 makes no such claim.

MySQL 8.4 LTS is the primary target and MySQL 9.7 is a compatibility target. MariaDB is deliberately rejected as `server_product_mismatch`. Production readiness and certification are not claimed until independently verified exact-commit hosted evidence is retained.
