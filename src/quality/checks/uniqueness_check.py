"""
DataObs — Uniqueness Check

Verifies that specified columns (or column combinations) have no duplicate values.
"""

from __future__ import annotations

import logging
from typing import Any, List

import sqlalchemy

from .base import BaseCheck, CheckResult
from .sql import table_name_from_dataset, validate_column_names

logger = logging.getLogger(__name__)


class UniquenessCheck(BaseCheck):
    check_type = "uniqueness"

    def run(self, config: dict, connection: Any) -> CheckResult:
        dataset = config["dataset"]
        columns: List[str] = validate_column_names(config["columns"])
        severity = config.get("severity", "critical")
        table_name = table_name_from_dataset(dataset)
        col_expr = ", ".join(columns)

        try:
            with connection.connect() as conn:
                result = conn.execute(
                    sqlalchemy.text(
                        f"SELECT COUNT(*) - COUNT(DISTINCT ({col_expr})) AS duplicate_count FROM {table_name}"
                    )
                )
                duplicate_count = result.scalar() or 0

            if duplicate_count > 0:
                return self._fail(
                    dataset=dataset,
                    message=f"Uniqueness violated: {duplicate_count:,} duplicate(s) found in {col_expr}",
                    severity=severity,
                    metric_value=float(duplicate_count),
                    threshold=0.0,
                    details={"columns": columns, "duplicate_count": duplicate_count},
                )

            return self._pass(
                dataset=dataset,
                message=f"Uniqueness check passed for {col_expr}",
                severity=severity,
                details={"columns": columns},
            )

        except Exception as exc:
            logger.exception("Uniqueness check error for %s", dataset)
            return self._error(dataset, exc)
