# Team 4 MySQL Database Collector v1 audit

- **Team / task:** Team 4 — Integrations and Collection; **Team 4: Build MySQL Database Collector v1**.
- **Audited base SHA:** `d4f511ebb331b74528426b91ce69bd24f8993eac`.
- **Terminal migration:** dynamically derived with `python scripts/release/current_terminal_migration.py` as `0030_team1_multi_broker_messaging_runtime`.
- **Migration doctor / immutability:** the executable registry and release metadata checks are the repository authority; local results are recorded in the final report. No migration is required because migration 0022's generic provider observations, runs, and tenant/environment OCC checkpoints suffice. No released migration is edited.
- **Registry before / after:** `aws, snowflake, databricks, bigquery, azure, trino, presto, postgres`; after: those providers plus `mysql` (the SDK returns them sorted).
- **Existing MySQL code:** no production MySQL collector or Connector/Python integration existed. Mentions were product documentation, redaction, dbt normalization, legacy scanning text, and generic quality paths. None supplies this provider.
- **Foundation reuse:** `DatabaseIdentity`, fixed statement registry, shared mutation rejection, bounded execution, structural fingerprinting, Integration SDK capabilities/observations/partial failures, generic persistence, and OCC checkpoints are reused.
- **Driver / Python:** Oracle's vendor-maintained `mysql-connector-python` is the sole optional dependency, pinned `>=26.7,<26.8`. PyPI reported GA 26.7.0 on 2026-08-12; the optional dependency is narrowly pinned to its 26.7 series. Live server qualification remains pending. Repository Python 3.11+ remains supported; local tests ran on the recorded final-report version.
- **TLS / secrets:** verified TLS with a trusted CA and identity verification is mandatory. Local infile is forced off. Closed configuration accepts shared secret references only; DSNs, inline credentials, dangerous connector knobs, and arbitrary session configuration are absent.
- **Metadata capabilities:** structural schemas, tables/views, columns, PK/unique/FK/CHECK presence, indexes, partitions, safe identity, deterministic snapshots, and opt-in aggregate freshness/profiling. Query history remains unsupported.
- **Server matrix:** MySQL 8.4 LTS primary target (8.4.10 requested baseline); MySQL 9.7 compatibility target where GA; neither is locally live-certified. Early Access is not certified. MariaDB is rejected.
- **Known limitations:** no hosted/live MySQL result in this checkout; no Performance Schema/query history; no samples, lineage, Team 2 intelligence, exact counts by default, or production-readiness claim; metadata visibility follows the collector principal.
