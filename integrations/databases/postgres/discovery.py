from __future__ import annotations

import re
from typing import Iterable

from .connection import query_tag

_SYSTEM_SCHEMAS = {"pg_catalog", "information_schema"}
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(identifier: str) -> str:
    if not _IDENT_RE.match(identifier):
        raise ValueError(f"invalid PostgreSQL identifier: {identifier!r}")
    return identifier


def quote_ident(identifier: str) -> str:
    return '"' + validate_identifier(identifier).replace('"', '""') + '"'


def _filter(
    rows: list[dict],
    allow_schemas: Iterable[str],
    deny_schemas: Iterable[str],
    allow_tables: Iterable[str],
    deny_tables: Iterable[str],
):
    allow_s = set(allow_schemas or [])
    deny_s = set(deny_schemas or []) | _SYSTEM_SCHEMAS
    allow_t = set(allow_tables or [])
    deny_t = set(deny_tables or [])
    return [
        r
        for r in rows
        if (not allow_s or r.get("schema") in allow_s)
        and r.get("schema") not in deny_s
        and (not allow_t or r.get("table") in allow_t)
        and r.get("table") not in deny_t
    ]


TABLE_SQL = """
SELECT current_database() AS database,
       n.nspname AS schema,
       c.relname AS table,
       CASE c.relkind WHEN 'r' THEN 'table' WHEN 'p' THEN 'partitioned_table' WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized_view' ELSE c.relkind::text END AS table_type,
       c.relkind::text AS relkind,
       c.relpersistence::text AS relation_persistence,
       pg_catalog.pg_get_userbyid(c.relowner) AS owner,
       obj_description(c.oid, 'pg_class') AS description,
       c.reltuples::bigint AS estimated_rows,
       pg_relation_size(c.oid) AS table_bytes,
       pg_indexes_size(c.oid) AS index_bytes,
       pg_total_relation_size(c.oid) AS total_bytes,
       s.last_analyze,
       s.last_autoanalyze,
       parent_ns.nspname AS partition_parent_schema,
       parent.relname AS partition_parent_table
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_catalog.pg_stat_all_tables s ON s.relid = c.oid
LEFT JOIN pg_catalog.pg_inherits inh ON inh.inhrelid = c.oid
LEFT JOIN pg_catalog.pg_class parent ON parent.oid = inh.inhparent
LEFT JOIN pg_catalog.pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
WHERE c.relkind IN ('r','p','v','m')
  AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY n.nspname, c.relname
"""
COLUMN_SQL = """
SELECT current_database() AS database,
       table_schema AS schema,
       table_name AS table,
       ordinal_position,
       column_name AS column,
       data_type AS type,
       udt_name AS native_type,
       is_nullable = 'YES' AS nullable,
       column_default AS default,
       identity_generation AS identity,
       is_generated AS generated,
       generation_expression
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog','information_schema')
ORDER BY table_schema, table_name, ordinal_position
"""
CONSTRAINT_SQL = """
SELECT tc.table_schema AS schema, tc.table_name AS table, tc.constraint_name, tc.constraint_type,
       kcu.column_name, ccu.table_schema AS foreign_schema, ccu.table_name AS foreign_table, ccu.column_name AS foreign_column,
       cc.check_clause
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu ON kcu.constraint_schema = tc.constraint_schema AND kcu.constraint_name = tc.constraint_name
LEFT JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_schema = tc.constraint_schema AND ccu.constraint_name = tc.constraint_name
LEFT JOIN information_schema.check_constraints cc ON cc.constraint_schema = tc.constraint_schema AND cc.constraint_name = tc.constraint_name
WHERE tc.table_schema NOT IN ('pg_catalog','information_schema')
ORDER BY tc.table_schema, tc.table_name, tc.constraint_name, kcu.ordinal_position
"""
INDEX_SQL = """
SELECT schemaname AS schema, tablename AS table, indexname AS index_name, indexdef AS index_definition
FROM pg_catalog.pg_indexes
WHERE schemaname NOT IN ('pg_catalog','information_schema')
ORDER BY schemaname, tablename, indexname
"""


def _rows(cur):
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def fetch_catalog(
    conn, scanner_id="scanner", task_id="task", allow_schemas=(), deny_schemas=(), allow_tables=(), deny_tables=()
):
    warnings: list[dict] = []
    out: dict[str, list[dict]] = {}
    with conn.cursor() as cur:
        for name, sql in (
            ("tables", TABLE_SQL),
            ("columns", COLUMN_SQL),
            ("constraints", CONSTRAINT_SQL),
            ("indexes", INDEX_SQL),
        ):
            try:
                cur.execute(query_tag(scanner_id, task_id, name) + sql)
                out[name] = _filter(_rows(cur), allow_schemas, deny_schemas, allow_tables, deny_tables)
            except Exception as exc:  # noqa: BLE001
                out[name] = []
                warnings.append(
                    {"capability": name, "reason": "privilege_unavailable", "message": str(exc.__class__.__name__)}
                )
    out["warnings"] = warnings
    return out
