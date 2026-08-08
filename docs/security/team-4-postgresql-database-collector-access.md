# PostgreSQL collector access

## Metadata only
Grant `CONNECT` only to required databases, `USAGE` only on required schemas, and catalog visibility/minimal statistics access. Never grant superuser, CREATEDB, CREATEROLE, REPLICATION or BYPASSRLS.

## Freshness and profiling
Grant `SELECT` only on explicitly approved relations, or use reviewed security-definer aggregate views. Do not grant blanket database-wide table SELECT. RLS remains effective: aggregates describe the collector principal's visible rows and cannot be called full-table counts when visibility is unknown.

## pg_stat_statements
Provider v1 does not collect query history and requires no extension access. Any later SQL-free aggregate contract needs a separate privacy review and permission profile; SQL, userid and role names must remain excluded.

Passwords and CA material use references, are resolved only at connection time, and never enter repr, evidence, errors, logs, traces or checkpoints. `verify-full` validates trust and hostname. `verify-ca` is explicit and does not provide hostname verification; weaker modes are rejected.
