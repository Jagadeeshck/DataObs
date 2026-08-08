from integrations.database import FixedStatementRegistry, Statement

from .discovery import COLUMN_SQL, CONSTRAINT_SQL, TABLE_SQL

INDEX_STRUCTURAL_SQL = """
SELECT ns.nspname AS schema, tbl.relname AS table, idx.relname AS index_name,
       i.indisunique AS unique, am.amname AS access_method,
       i.indexprs IS NOT NULL AS expression_index, i.indpred IS NOT NULL AS partial_index,
       i.indisvalid AS valid, i.indisready AS ready, i.indisprimary AS primary,
       pg_relation_size(idx.oid) AS estimated_bytes
FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class idx ON idx.oid=i.indexrelid
JOIN pg_catalog.pg_class tbl ON tbl.oid=i.indrelid JOIN pg_catalog.pg_namespace ns ON ns.oid=tbl.relnamespace
JOIN pg_catalog.pg_am am ON am.oid=idx.relam WHERE ns.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY ns.nspname,tbl.relname,idx.relname
"""

REGISTRY = FixedStatementRegistry(
    (
        Statement("health", "SELECT 1 AS reachable", 1),
        Statement("relations", TABLE_SQL, 1000000),
        Statement("columns", COLUMN_SQL, 5000000),
        Statement("constraints", CONSTRAINT_SQL, 5000000),
        Statement("indexes", INDEX_STRUCTURAL_SQL, 2000000),
    )
)
