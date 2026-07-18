from __future__ import annotations

from .connection import query_tag

TABLE_SQL = """
SELECT current_database() AS database, n.nspname AS schema, c.relname AS table, c.relkind, c.relpersistence,
       pg_catalog.pg_get_userbyid(c.relowner) AS owner, obj_description(c.oid) AS description,
       c.reltuples::bigint AS estimated_rows, pg_total_relation_size(c.oid) AS total_bytes
FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','p','v','m') AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY n.nspname,c.relname
"""
COLUMN_SQL = """
SELECT current_database() AS database, table_schema AS schema, table_name AS table, column_name AS column,
       data_type AS type, udt_name AS native_type, is_nullable='YES' AS nullable, column_default AS default
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog','information_schema')
ORDER BY table_schema, table_name, ordinal_position
"""


def fetch_catalog(conn, scanner_id="scanner", task_id="task"):
    with conn.cursor() as cur:
        cur.execute(query_tag(scanner_id, task_id, "discover") + TABLE_SQL)
        tables = cur.fetchall()
        table_cols = [d.name for d in cur.description]
        cur.execute(query_tag(scanner_id, task_id, "columns") + COLUMN_SQL)
        cols = cur.fetchall()
        col_cols = [d.name for d in cur.description]
    return {"tables": [dict(zip(table_cols, r)) for r in tables], "columns": [dict(zip(col_cols, r)) for r in cols]}
