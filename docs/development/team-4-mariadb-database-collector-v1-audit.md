# Team 4 MariaDB database collector v1 audit

- **Team / task:** Team 4 — `Team 4: Build MariaDB Database Collector v1`.
- **Audited SHA:** `a7e27f119e426b2ed2967912fe0bdc6d78d6ba03`.
- **Terminal migration / doctor:** `0030_team1_multi_broker_messaging_runtime`; no migration is required because generic observations and OCC checkpoints are reused; released migrations remain unchanged.
- **Audit scope/searches:** `integrations/database`, PostgreSQL, MySQL, Collection Manager, collector SDK, and Elastic store were inspected for MariaDB/MySQL-family catalogs, `information_schema`, `performance_schema`, tables, columns, statistics, partitions, system versioning, sequences, and user statistics.
- **Registry:** aws, snowflake, databricks, bigquery, azure, trino, presto, postgres, mysql, mariadb (registry API returns sorted order).
- **Safe reuse:** engine-neutral identity, executor/safety, observations, fingerprints, aggregate freshness/profiling patterns, persistence-before-checkpoint and OCC. MySQL remains separate; no MySQL provider modules are imported by MariaDB.
- **MariaDB differences:** mandatory MariaDB product marker, MariaDB table categories, Aria/ColumnStore/MyRocks, UUID/INET types, `IGNORED` indexes, optional userstat/Performance Schema.
- **Driver/native dependency:** vendor `mariadb==1.1.14`, Python >=3.8; source builds require MariaDB Connector/C >=3.3.1. Wheels may bundle native components; deployed native version must be recorded by hosted evidence.
- **TLS/hostname:** TLS and CA verification are mandatory. `ssl_verify_cert=True` delegates chain and hostname validation to Connector/C; no separate identity option exists. Certification is blocked if the deployed native stack cannot prove hostname validation.
- **Compatibility:** MariaDB 11.8 LTS primary and 11.4 LTS secondary. Rolling/preview releases are not certified automatically.
- **Metadata:** bounded structural catalogs only; no raw expressions, query text, business/history rows, sequence values, or mandatory optional statistics.
- **Known limitations:** live tests and hosted exact-commit/native-version evidence are pending; status is `functional_unvalidated`; no production-readiness claim.
