from datetime import datetime, timedelta, timezone

from .. import sql
from ..normalisation import observation, safe, value

SAFE = {
    "jobs": (
        "job_id",
        "parent_job_id",
        "job_type",
        "statement_type",
        "state",
        "priority",
        "creation_time",
        "start_time",
        "end_time",
        "total_slot_ms",
        "total_bytes_processed",
        "total_bytes_billed",
        "cache_hit",
        "reservation_id",
        "edition",
        "error_reason",
    ),
    "job_timeline": (
        "bucket_time",
        "job_type",
        "reservation_id",
        "edition",
        "slot_ms",
        "running_count",
        "pending_count",
    ),
    "storage": (
        "table_schema",
        "table_name",
        "table_type",
        "active_logical_bytes",
        "long_term_logical_bytes",
        "current_physical_bytes",
        "total_physical_bytes",
        "time_travel_physical_bytes",
        "fail_safe_physical_bytes",
        "deleted",
    ),
}


def collect(client, context, cfg, project, location, family):
    limit = int(
        cfg.jobs.get("maximum_rows_per_location", 5000)
        if family != "storage"
        else cfg.storage.get("maximum_rows_per_location", 50000)
    )
    q = getattr(sql, family)(project.project_id, location, limit)
    end = datetime.now(timezone.utc)
    start = end - timedelta(seconds=int(cfg.jobs.get("lookback_seconds", 3600)))
    job = client.invoke(
        "fixed_query",
        q.sql,
        job_config={
            "query_parameters": {"start_time": start, "end_time": end},
            "maximum_bytes_billed": int(cfg.query_execution.get("maximum_bytes_billed", 100000000)),
            "use_legacy_sql": False,
        },
        location=location,
        timeout=int(cfg.query_execution.get("timeout_seconds", 60)),
    )
    for row in list(job)[:limit]:
        ev = safe(row, SAFE[family])
        native = "|".join(
            str(ev.get(k, ""))
            for k in (
                ("creation_time", "job_id")
                if family == "jobs"
                else (
                    ("bucket_time", "reservation_id", "job_type")
                    if family == "job_timeline"
                    else ("table_schema", "table_name")
                )
            )
        )
        if family == "jobs":
            ev["script_parent"] = ev.get("statement_type") == "SCRIPT"
            ev["included_in_consumption_aggregate"] = not ev["script_parent"]
        if family == "storage":
            ev.update({"source_freshness": "delayed_source", "evidence_state": "measured"})
        yield observation(context, project.project_id, location, family, native, native, ev)
