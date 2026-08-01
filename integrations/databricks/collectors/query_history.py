from ..normalisation import observation
from ..statement_execution import execute_fixed

FIELDS = (
    "statement_id",
    "execution_status",
    "statement_type",
    "compute_type",
    "warehouse_id",
    "waiting_at_capacity_duration_ms",
    "execution_duration_ms",
    "compilation_duration_ms",
    "total_task_duration_ms",
    "result_fetch_duration_ms",
    "start_time",
    "end_time",
    "update_time",
    "read_partitions",
    "pruned_files",
    "read_files",
    "read_rows",
    "produced_rows",
    "read_bytes",
    "error_category",
)


def collect(client, context, cfg, parameters):
    section = cfg.system_tables.get("query_history", {})
    if not cfg.system_tables.get("enabled", False) or not section.get("enabled", False):
        return
    rows = execute_fixed(
        client,
        "query_history",
        cfg.system_tables["sql_warehouse_id"],
        parameters,
        timeout_seconds=cfg.limits["statement_timeout_seconds"],
        maximum_rows=int(section.get("maximum_rows", 5000)),
        maximum_bytes=cfg.limits["maximum_result_bytes"],
    )
    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        safe = dict(zip(FIELDS, row))
        sid = str(safe["statement_id"])
        safe["preview"] = True
        safe["workspace_filtered"] = True
        yield observation(context, cfg.expected_workspace_id, cfg.cloud, "query_history", sid, sid[:16], safe)
