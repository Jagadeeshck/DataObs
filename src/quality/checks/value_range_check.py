"""
DataObs — Value Range Check

Verifies that numeric column values fall within defined min/max bounds.
"""

from __future__ import annotations

import logging
from typing import Any

import sqlalchemy

from .base import BaseCheck, CheckResult
from .sql import table_name_from_dataset, validate_simple_identifier

logger = logging.getLogger(__name__)


class ValueRangeCheck(BaseCheck):
    check_type = "value_range"

    def run(self, config: dict, connection: Any) -> CheckResult:
        dataset = config["dataset"]
        column = validate_simple_identifier(config["column"], "column")
        min_value = config.get("min_value")
        max_value = config.get("max_value")
        severity = config.get("severity", "high")
        table_name = table_name_from_dataset(dataset)

        try:
            with connection.connect() as conn:
                result = conn.execute(sqlalchemy.text(f"SELECT MIN({column}), MAX({column}) FROM {table_name}"))
                row = result.fetchone()
                actual_min, actual_max = row[0], row[1]

            violations = []
            if min_value is not None and actual_min is not None and actual_min < min_value:
                violations.append(f"min({column})={actual_min} < allowed min={min_value}")
            if max_value is not None and actual_max is not None and actual_max > max_value:
                violations.append(f"max({column})={actual_max} > allowed max={max_value}")

            if violations:
                return self._fail(
                    dataset=dataset,
                    message=f"Value range violation in {column}: {'; '.join(violations)}",
                    severity=severity,
                    details={
                        "column": column,
                        "actual_min": actual_min,
                        "actual_max": actual_max,
                        "allowed_min": min_value,
                        "allowed_max": max_value,
                    },
                )

            return self._pass(
                dataset=dataset,
                message=f"Value range check passed for {column} [{actual_min}, {actual_max}]",
                severity=severity,
                details={"column": column, "actual_min": actual_min, "actual_max": actual_max},
            )

        except Exception as exc:
            logger.exception("Value range check error for %s", dataset)
            return self._error(dataset, exc)
