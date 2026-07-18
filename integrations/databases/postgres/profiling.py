from __future__ import annotations

from .connection import query_tag
from .discovery import quote_ident

SECRET_NAMES = ("password", "secret", "token", "ssn", "credit_card")


def _qtable(table: str) -> str:
    return ".".join(quote_ident(p) for p in table.split("."))


def profile_table(conn, table, columns, *, enable=False, top_values=False, scanner_id="scanner", task_id="task"):
    if not enable:
        return {"profiling": "disabled"}
    metrics = {"raw_rows_persisted": False, "partial_success": False, "denied_columns": []}
    qtable = _qtable(table)
    with conn.cursor() as cur:
        cur.execute("BEGIN READ ONLY")
        cur.execute(query_tag(scanner_id, task_id, "profile-row-count") + f"SELECT count(*) FROM {qtable}")
        row_count = cur.fetchone()[0]
        metrics["row_count"] = row_count
        metrics["columns"] = {}
        for c in columns:
            name = c["name"] if isinstance(c, dict) else str(c)
            lower = name.lower()
            if any(s in lower for s in SECRET_NAMES):
                metrics["denied_columns"].append({"column": name, "reason": "sensitive_name"})
                metrics["partial_success"] = True
                continue
            qcol = quote_ident(name)
            cur.execute(
                query_tag(scanner_id, task_id, "profile-column")
                + f"SELECT count(*) FILTER (WHERE {qcol} IS NULL), count(DISTINCT {qcol}), min({qcol})::text, max({qcol})::text FROM {qtable}"
            )
            nulls, distinct, min_v, max_v = cur.fetchone()
            metrics["columns"][name] = {
                "null_count": nulls,
                "distinct_count": distinct,
                "null_rate": nulls / row_count if row_count else 0,
                "uniqueness_ratio": distinct / row_count if row_count else 0,
                "min": min_v,
                "max": max_v,
            }
        cur.execute("COMMIT")
    return metrics
