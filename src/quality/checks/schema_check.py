"""
DataObs — Schema Change Check

Detects breaking schema changes (column removal, type changes) by comparing
the current schema against the last known-good schema stored in Elasticsearch.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from elasticsearch import Elasticsearch

from .base import BaseCheck, CheckResult

logger = logging.getLogger(__name__)


class SchemaCheck(BaseCheck):
    check_type = "schema_change"

    def __init__(self, es_client: Elasticsearch):
        self.es = es_client

    def run(self, config: dict, connection: Any) -> CheckResult:
        """
        Config keys:
          dataset: str
          alert_on: List[str]   # column_removed | type_changed | column_added
          severity: str
        """
        dataset = config["dataset"]
        alert_on = config.get("alert_on", ["column_removed", "type_changed"])
        severity = config.get("severity", "critical")

        try:
            current_schema = self._get_current_schema(dataset, connection)
            previous_schema = self._get_stored_schema(dataset)

            if previous_schema is None:
                # First run: store baseline
                self._store_schema(dataset, current_schema)
                return self._pass(
                    dataset=dataset,
                    message="Schema baseline established (first run)",
                    severity="low",
                    details={"schema": current_schema},
                )

            changes = self._compare_schemas(previous_schema, current_schema)
            violations = [c for c in changes if c["change_type"] in alert_on]

            if violations:
                return self._fail(
                    dataset=dataset,
                    message=f"Schema change detected: {len(violations)} violation(s)",
                    severity=severity,
                    details={"changes": violations, "current_schema": current_schema},
                )

            # Update stored schema if non-breaking changes found
            if changes:
                self._store_schema(dataset, current_schema)
                logger.info("Schema updated for %s (non-breaking changes): %d", dataset, len(changes))

            return self._pass(
                dataset=dataset,
                message="Schema check passed",
                severity=severity,
                details={"schema": current_schema, "changes": changes},
            )

        except Exception as exc:
            logger.exception("Schema check error for %s", dataset)
            return self._error(dataset, exc)

    def _get_current_schema(self, dataset: str, connection: Any) -> Dict[str, str]:
        """Query information_schema for column types."""
        import sqlalchemy
        table_name = dataset.split(".")[-1]
        schema_name = dataset.split(".")[-2] if dataset.count(".") >= 2 else "public"

        with connection.connect() as conn:
            result = conn.execute(
                sqlalchemy.text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table "
                    "ORDER BY ordinal_position"
                ),
                {"schema": schema_name, "table": table_name},
            )
            return {row[0]: row[1] for row in result}

    def _get_stored_schema(self, dataset: str) -> Dict[str, str] | None:
        """Retrieve the last stored schema from Elasticsearch."""
        try:
            response = self.es.search(
                index="dataobs-schema-registry",
                query={"term": {"dataset.keyword": dataset}},
                sort=[{"@timestamp": {"order": "desc"}}],
                size=1,
            )
            hits = response["hits"]["hits"]
            if hits:
                return hits[0]["_source"].get("schema", {})
        except Exception:
            pass
        return None

    def _store_schema(self, dataset: str, schema: Dict[str, str]) -> None:
        """Store current schema as the new baseline."""
        from datetime import datetime, timezone
        self.es.index(
            index="dataobs-schema-registry",
            document={
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "dataset": dataset,
                "schema": schema,
                "column_count": len(schema),
            },
        )

    def _compare_schemas(
        self, previous: Dict[str, str], current: Dict[str, str]
    ) -> List[Dict]:
        """Return a list of schema changes between two schemas."""
        changes = []

        for col, dtype in previous.items():
            if col not in current:
                changes.append({"change_type": "column_removed", "column": col, "previous_type": dtype})
            elif current[col] != dtype:
                changes.append({"change_type": "type_changed", "column": col, "previous_type": dtype, "new_type": current[col]})

        for col, dtype in current.items():
            if col not in previous:
                changes.append({"change_type": "column_added", "column": col, "new_type": dtype})

        return changes
