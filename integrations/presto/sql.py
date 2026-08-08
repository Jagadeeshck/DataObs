from integrations.sql_engine import FixedStatement, FixedStatementRegistry, quote_identifier

SOURCE = "dataobs-collector"
STATEMENTS = (
    FixedStatement("validate", "SELECT 1 AS reachable", "identity"),
    FixedStatement("version", "SELECT version() AS server_version", "identity"),
    FixedStatement(
        "catalogs",
        "SELECT catalog_name, connector_name FROM system.metadata.catalogs ORDER BY catalog_name",
        "catalogs",
    ),
    FixedStatement(
        "cluster",
        "SELECT count(node_id) AS visible_nodes, count_if(state = 'active') AS active_nodes, count_if(state <> 'active') AS inactive_nodes, node_version, state FROM system.runtime.nodes GROUP BY node_version, state ORDER BY node_version, state",
        "cluster_health",
    ),
    FixedStatement(
        "queries",
        "SELECT query_id, state, queued_time_ms, analysis_time_ms, distributed_planning_time_ms, created, started, last_heartbeat, end, error_type, error_code FROM system.runtime.queries WHERE (source IS NULL OR source <> 'dataobs-collector') AND created >= ? ORDER BY created, query_id LIMIT ?",
        "runtime_queries",
    ),
    FixedStatement(
        "tasks",
        "SELECT query_id, count(task_id) AS task_count, sum(total_splits) AS total_splits, sum(queued_splits) AS queued_splits, sum(running_splits) AS running_splits, sum(completed_splits) AS completed_splits, sum(raw_input_bytes) AS raw_input_bytes, sum(raw_input_rows) AS raw_input_rows, sum(output_bytes) AS output_bytes, sum(output_rows) AS output_rows FROM system.runtime.tasks GROUP BY query_id ORDER BY query_id LIMIT ?",
        "runtime_tasks",
    ),
)
REGISTRY = FixedStatementRegistry(STATEMENTS)


def catalog_registry(catalog: str) -> FixedStatementRegistry:
    c = quote_identifier(catalog)
    return FixedStatementRegistry(
        (
            FixedStatement(
                "schemas",
                f"SELECT catalog_name, schema_name FROM {c}.information_schema.schemata ORDER BY schema_name",
                "schemas",
            ),
            FixedStatement(
                "relations",
                f"SELECT table_catalog, table_schema, table_name, table_type FROM {c}.information_schema.tables ORDER BY table_schema, table_name",
                "relations",
            ),
            FixedStatement(
                "columns",
                f"SELECT table_catalog, table_schema, table_name, column_name, ordinal_position, data_type, is_nullable FROM {c}.information_schema.columns ORDER BY table_schema, table_name, ordinal_position",
                "columns",
            ),
        )
    )
