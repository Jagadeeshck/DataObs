from ..normalisation import observation
from ..statement_execution import execute_fixed

EVENTS = {"STARTING", "RUNNING", "STOPPING", "STOPPED", "SCALED_UP", "SCALED_DOWN"}


def collect(client, context, cfg, parameters):
    section = cfg.system_tables.get("warehouse_events", {})
    if not cfg.system_tables.get("enabled", False) or not section.get("enabled", False):
        return
    rows = execute_fixed(
        client,
        "warehouse_events",
        cfg.system_tables["sql_warehouse_id"],
        parameters,
        timeout_seconds=cfg.limits["statement_timeout_seconds"],
        maximum_rows=int(section.get("maximum_rows", 5000)),
        maximum_bytes=cfg.limits["maximum_result_bytes"],
    )
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 5 or str(row[0]) != cfg.expected_workspace_id:
            continue
        event = str(row[2]).upper()
        if event not in EVENTS:
            continue
        evidence = {"warehouse_id": row[1], "event_type": event, "cluster_count": row[3], "event_time": row[4]}
        yield observation(
            context,
            cfg.expected_workspace_id,
            cfg.cloud,
            "warehouse_event",
            f"{row[4]}:{row[1]}:{event}",
            event,
            evidence,
        )
