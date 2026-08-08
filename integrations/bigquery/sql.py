from __future__ import annotations

from dataclasses import dataclass

from .identifiers import location_id, project_id


@dataclass(frozen=True)
class FixedQuery:
    name: str
    sql: str
    parameters: tuple[str, ...]


def _view(project, location, name):
    return f"`{project_id(project)}.region-{location_id(location)}.INFORMATION_SCHEMA.{name}`"


def jobs(project, location, limit):
    limit = max(1, min(int(limit), 50000))
    return FixedQuery(
        "jobs",
        f"""SELECT job_id, parent_job_id, job_type, statement_type, state, priority, creation_time, start_time, end_time, total_slot_ms, total_bytes_processed, total_bytes_billed, cache_hit, reservation_id, edition, error_result.reason AS error_reason\nFROM {_view(project,location,'JOBS_BY_PROJECT')}\nWHERE creation_time >= @start_time AND creation_time < @end_time\nORDER BY creation_time, job_id\nLIMIT {limit}""",
        ("start_time", "end_time"),
    )


def timeline(project, location, limit):
    limit = max(1, min(int(limit), 50000))
    return FixedQuery(
        "job_timeline",
        f"""SELECT TIMESTAMP_BUCKET(period_start, INTERVAL 60 SECOND) AS bucket_time, job_type, reservation_id, edition, SUM(period_slot_ms) AS slot_ms, COUNTIF(state='RUNNING') AS running_count, COUNTIF(state='PENDING') AS pending_count\nFROM {_view(project,location,'JOBS_TIMELINE_BY_PROJECT')}\nWHERE period_start >= @start_time AND period_start < @end_time AND COALESCE(statement_type, '') != 'SCRIPT'\nGROUP BY bucket_time, job_type, reservation_id, edition\nORDER BY bucket_time, reservation_id, job_type\nLIMIT {limit}""",
        ("start_time", "end_time"),
    )


def storage(project, location, limit):
    limit = max(1, min(int(limit), 50000))
    return FixedQuery(
        "storage",
        f"""SELECT table_schema, table_name, table_type, active_logical_bytes, long_term_logical_bytes, current_physical_bytes, total_physical_bytes, time_travel_physical_bytes, fail_safe_physical_bytes, deleted\nFROM {_view(project,location,'TABLE_STORAGE_BY_PROJECT')}\nWHERE storage_last_modified_time >= @start_time AND storage_last_modified_time < @end_time\nORDER BY storage_last_modified_time, table_schema, table_name\nLIMIT {limit}""",
        ("start_time", "end_time"),
    )


TEMPLATES = (jobs, timeline, storage)
