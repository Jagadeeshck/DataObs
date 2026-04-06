"""
DataObs — Referential Integrity Check

Verifies that FK columns in a table reference existing records in the parent table.
"""

from __future__ import annotations

import logging
from typing import Any

import sqlalchemy

from .base import BaseCheck, CheckResult

logger = logging.getLogger(__name__)


class ReferentialIntegrityCheck(BaseCheck):
    check_type = "referential_integrity"

    def run(self, config: dict, connection: Any) -> CheckResult:
        dataset = config["dataset"]
        column = config["column"]
        references = config["references"]   # e.g. "schema.parent_table.id"
        severity = config.get("severity", "high")

        parts = references.split(".")
        ref_table = ".".join(parts[:-1])
        ref_column = parts[-1]
        child_table = dataset.split(".")[-1]

        try:
            with connection.connect() as conn:
                result = conn.execute(
                    sqlalchemy.text(
                        f"SELECT COUNT(*) FROM {child_table} c "
                        f"LEFT JOIN {ref_table} p ON c.{column} = p.{ref_column} "
                        f"WHERE p.{ref_column} IS NULL AND c.{column} IS NOT NULL"
                    )
                )
                orphan_count = result.scalar() or 0

            if orphan_count > 0:
                return self._fail(
                    dataset=dataset,
                    message=f"Referential integrity violated: {orphan_count:,} orphan records in {column} (references {references})",
                    severity=severity,
                    metric_value=float(orphan_count),
                    threshold=0.0,
                    details={"column": column, "references": references, "orphan_count": orphan_count},
                )

            return self._pass(
                dataset=dataset,
                message=f"Referential integrity check passed: {column} -> {references}",
                severity=severity,
            )

        except Exception as exc:
            logger.exception("Referential integrity check error for %s", dataset)
            return self._error(dataset, exc)
