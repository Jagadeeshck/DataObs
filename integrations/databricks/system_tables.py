QUERY_HISTORY_SQL = """SELECT statement_id, execution_status, statement_type, compute_type, warehouse_id, waiting_at_capacity_duration_ms, execution_duration_ms, compilation_duration_ms, total_task_duration_ms, result_fetch_duration_ms, start_time, end_time, update_time, read_partitions, pruned_files, read_files, read_rows, produced_rows, read_bytes, error_category FROM system.query.history WHERE workspace_id = :workspace_id AND update_time >= :start_time AND update_time < :end_time ORDER BY update_time, statement_id LIMIT :row_limit"""
WAREHOUSE_EVENTS_SQL = """SELECT workspace_id, warehouse_id, event_type, cluster_count, event_time FROM system.compute.warehouse_events WHERE workspace_id = :workspace_id AND event_time >= :start_time AND event_time < :end_time ORDER BY event_time, warehouse_id, event_type LIMIT :row_limit"""


def validate_templates() -> None:
    forbidden = (
        "SELECT *",
        "STATEMENT_TEXT",
        "ERROR_MESSAGE",
        "EXECUTED_BY",
        "SESSION_ID",
        "CLIENT_APPLICATION",
        "QUERY_TAGS",
    )
    for sql in (QUERY_HISTORY_SQL, WAREHOUSE_EVENTS_SQL):
        upper = " ".join(sql.upper().split())
        if (
            any(word in upper for word in forbidden)
            or "WORKSPACE_ID = :WORKSPACE_ID" not in upper
            or " ORDER BY " not in upper
            or " LIMIT :ROW_LIMIT" not in upper
        ):
            raise ValueError("unsafe system-table template")
