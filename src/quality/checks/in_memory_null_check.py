"""Deterministic nullness check for already-materialized records."""

from __future__ import annotations

from typing import Any

from .base import BaseCheck, CheckResult


class InMemoryNullCheck(BaseCheck):
    """Evaluate nullness without requiring a database connection."""

    check_type = "null_check"

    def run(self, config: dict, connection: Any) -> CheckResult:
        dataset = str(config["dataset"])
        column = str(config["column"])
        rows = list(config["rows"])
        maximum = float(config.get("max_null_pct", 0.0))
        null_count = sum(row.get(column) is None for row in rows)
        null_pct = (null_count / len(rows) * 100.0) if rows else 0.0
        details = {"column": column, "row_count": len(rows), "null_count": null_count, "null_pct": null_pct}
        if null_pct > maximum:
            return self._fail(
                dataset,
                f"Null rate {null_pct:.2f}% exceeds {maximum:.2f}%",
                config.get("severity", "high"),
                details=details,
                metric_value=null_pct,
                threshold=maximum,
            )
        return self._pass(
            dataset,
            f"Null rate {null_pct:.2f}% is within threshold",
            config.get("severity", "low"),
            details=details,
            metric_value=null_pct,
            threshold=maximum,
        )
