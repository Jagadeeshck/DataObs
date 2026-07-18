# PostgreSQL DataObs Connector

Reference connector for metadata-only PostgreSQL discovery and optional aggregate profiling. It uses schema allow/deny filters, read-only/timeout intent, query tagging, canonical schema fingerprints, checkpoints, and never persists raw business rows.

## Least privilege

Use a dedicated PostgreSQL role with `CONNECT`, schema `USAGE`, catalog visibility and narrowly scoped `SELECT` only when opt-in aggregate profiling or freshness queries are enabled. DataObs discovery uses explicit `information_schema` and `pg_catalog` projections and does not issue `SELECT *` for catalog discovery.

## Secrets

Connector passwords must use `env://`, `file://` or `k8s-file://` references. Secret values are resolved in-process and redacted from reprs, API payloads, task payloads, logs and Elasticsearch documents.
