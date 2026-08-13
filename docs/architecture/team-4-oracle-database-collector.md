# Team 4 Oracle database collector v1

The `oracle` v1 provider reuses `FixedStatementRegistry`, `BoundedStatementExecutor`, `DatabaseIdentity`, SDK observations, and Collection Manager persistence/checkpoints. It uses fixed `ALL_*` metadata queries, feature-detects optional vector dictionary columns, and emits redacted partial failures. One configured TCPS service/PDB is one integration; it never enumerates CDBs, RAC, or Data Guard.

Metadata includes accessible schemas, tables, views, materialized views, safe columns, constraints/FKs, indexes, and bounded partitions. Definitions, defaults, statistics values, expressions, CHECK text, and partition boundaries are excluded. Fingerprints contain structure only. `raw_rows_persisted=false`.

Freshness is explicit timestamp-column MAX policy. Profiling defaults off and permits bounded aggregates only. Query history, AWR, ASH, SQL text, lineage, logs, costs, events, and Data Quality are unsupported.
