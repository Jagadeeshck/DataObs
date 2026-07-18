from __future__ import annotations

from datetime import datetime, timezone

from .connection import query_tag
from .discovery import quote_ident


def measure_freshness(
    conn, table, timestamp_column=None, external_watermark=None, scanner_id="scanner", task_id="task"
):
    observed = datetime.now(timezone.utc)
    if external_watermark:
        latest = external_watermark
        strategy = "external_watermark"
        confidence = "high"
    elif timestamp_column and table:
        parts = [quote_ident(p) for p in table.split(".")]
        with conn.cursor() as cur:
            cur.execute(
                query_tag(scanner_id, task_id, "freshness")
                + f"SELECT max({quote_ident(timestamp_column)}) AS latest_source_timestamp FROM {'.'.join(parts)}"
            )
            latest = cur.fetchone()[0]
            strategy = "max_timestamp_column"
            confidence = "high" if latest is not None else "medium"
    else:
        latest = None
        strategy = "catalog_metadata"
        confidence = "low"
    return {
        "observed_at": observed.isoformat(),
        "latest_source_timestamp": latest.isoformat() if hasattr(latest, "isoformat") else latest,
        "strategy": strategy,
        "confidence": confidence,
        "sla_status": "unknown" if latest is None else "ok",
    }
