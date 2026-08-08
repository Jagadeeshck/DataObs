"""
Elasticsearch-backed store for distribution drift baselines.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/24
"""

from __future__ import annotations

from typing import Optional

from src.quality.checks.distribution_drift_check import DriftBaseline

INDEX_PREFIX = "dataobs-drift-baselines"


class ElasticsearchBaselineStore:
    """
    Persists DriftBaseline objects to Elasticsearch.

    Args:
        es_client: elasticsearch.Elasticsearch instance.
        tenant_id: Tenant identifier (used in index name).
    """

    def __init__(self, es_client: object, tenant_id: str = "default") -> None:
        raise RuntimeError(
            "ElasticsearchBaselineStore is deprecated: use the migration-managed canonical monitor repository"
        )

    def _ensure_index(self) -> None:
        """Dynamic index creation was removed; released only for import compatibility."""
        raise RuntimeError("dynamic baseline index creation is prohibited")

    def _doc_id(self, table: str, column: str) -> str:
        return f"{table}__{column}"

    def get(self, table: str, column: str) -> Optional[DriftBaseline]:
        try:
            resp = self._es.get(index=self._index, id=self._doc_id(table, column))  # type: ignore[attr-defined]
            src = resp["_source"]
            return DriftBaseline(
                column=src["column"],
                table=src["table"],
                mean=src.get("mean", 0.0),
                std=src.get("std", 0.0),
                null_rate=src.get("null_rate", 0.0),
                sample_count=src.get("sample_count", 0),
            )
        except Exception:
            return None

    def put(self, baseline: DriftBaseline) -> None:
        from datetime import datetime, timezone

        self._es.index(  # type: ignore[attr-defined]
            index=self._index,
            id=self._doc_id(baseline.table, baseline.column),
            body={
                "table": baseline.table,
                "column": baseline.column,
                "mean": baseline.mean,
                "std": baseline.std,
                "null_rate": baseline.null_rate,
                "sample_count": baseline.sample_count,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            refresh="wait_for",
        )
