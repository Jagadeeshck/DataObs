from __future__ import annotations

from datetime import datetime, timezone

from .connection import query_tag


def measure_freshness(
    conn, table, timestamp_column=None, external_watermark=None, scanner_id="scanner", task_id="task"
):
    observed = datetime.now(timezone.utc)
    if external_watermark:
        latest = external_watermark
        strategy = "external_watermark"
        confidence = "high"
    elif timestamp_column:
        with conn.cursor() as cur:
            cur.execute(
                query_tag(scanner_id, task_id, "freshness")
                + f'SELECT max("{timestamp_column}") AS latest_source_timestamp FROM {table}'
            )
            latest = cur.fetchone()[0]
            strategy = "max_timestamp_column"
            confidence = "high"
    else:
        latest = None
        strategy = "catalog_metadata"
        confidence = "low"
    return {
        "observed_at": observed.isoformat(),
        "latest_source_timestamp": latest.isoformat() if hasattr(latest, "isoformat") else latest,
        "strategy": strategy,
        "confidence": confidence,
    }
