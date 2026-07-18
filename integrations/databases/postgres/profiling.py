from __future__ import annotations

from .connection import query_tag

SECRET_NAMES = ("password", "secret", "token", "ssn", "credit_card")


def profile_table(conn, table, columns, *, enable=False, top_values=False, scanner_id="scanner", task_id="task"):
    if not enable:
        return {"profiling": "disabled"}
    metrics = {}
    with conn.cursor() as cur:
        cur.execute("BEGIN READ ONLY")
        cur.execute(query_tag(scanner_id, task_id, "profile-row-count") + f"SELECT count(*) FROM {table}")
        metrics["row_count"] = cur.fetchone()[0]
        metrics["columns"] = {}
        for c in columns:
            name = c["name"]
            lower = name.lower()
            if any(s in lower for s in SECRET_NAMES):
                continue
            cur.execute(
                query_tag(scanner_id, task_id, "profile-column")
                + f'SELECT count(*) FILTER (WHERE "{name}" IS NULL), count(DISTINCT "{name}") FROM {table}'
            )
            nulls, distinct = cur.fetchone()
            metrics["columns"][name] = {
                "null_count": nulls,
                "distinct_count": distinct,
                "null_rate": nulls / metrics["row_count"] if metrics["row_count"] else 0,
            }
    return metrics
