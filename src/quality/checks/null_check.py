"""
DataObs — Null Check

Verifies that specified columns do not exceed acceptable null rates.
"""

from __future__ import annotations

import logging
from typing import Any

import sqlalchemy

from .base import BaseCheck, CheckResult

logger = logging.getLogger(__name__)


class NullCheck(BaseCheck):
    check_type = "null_check"

    def run(self, config: dict, connection: Any) -> CheckResult:
        """
        Config keys:
          dataset: str                    # table or view name
          columns: List[str]              # columns to check
          max_null_pct: float             # e.g. 0.0 = no nulls allowed, 5.0 = up to 5%
          severity: str
        """
        dataset = config["dataset"]
        columns = config["columns"]
        max_null_pct = config.get("max_null_pct", 0.0)
        severity = config.get("severity", "high")

        try:
            table_name = dataset.split(".")[-1]
            with connection.connect() as conn:
                # Get total row count
                total_result = conn.execute(sqlalchemy.text(f"SELECT COUNT(*) FROM {table_name}"))
                total_rows = total_result.scalar() or 0

                if total_rows == 0:
                    return self._pass(dataset, "Table is empty, null check skipped.", severity="low")

                violations = {}
                for col in columns:
                    null_result = conn.execute(
                        sqlalchemy.text(f"SELECT COUNT(*) FROM {table_name} WHERE {col} IS NULL")
                    )
                    null_count = null_result.scalar() or 0
                    null_pct = (null_count / total_rows) * 100
                    if null_pct > max_null_pct:
                        violations[col] = {"null_count": null_count, "null_pct": round(null_pct, 4)}

                if violations:
                    return self._fail(
                        dataset=dataset,
                        message=f"Null check failed for columns: {list(violations.keys())}",
                        severity=severity,
                        details={"violations": violations, "total_rows": total_rows, "max_null_pct": max_null_pct},
                        metric_value=max(v["null_pct"] for v in violations.values()),
                        threshold=max_null_pct,
                    )

                return self._pass(
                    dataset=dataset,
                    message=f"All {len(columns)} columns pass null check (max_null_pct={max_null_pct}%)",
                    severity=severity,
                    details={"columns_checked": columns, "total_rows": total_rows},
                )

        except Exception as exc:
            logger.exception("Null check error for %s", dataset)
            return self._error(dataset, exc)
