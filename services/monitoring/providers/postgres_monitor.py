"""Canonical monitor provider backed by the reviewed PostgreSQL aggregate AST."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from services.monitoring.providers.base import CapabilityState, ProviderBudget, ProviderResult
from services.monitoring.providers.postgres_aggregate import Aggregate, AggregateExpression


class PostgresMonitorProvider:
    OPERATIONS = {
        "freshness": Aggregate.MAX_TIMESTAMP,
        "volume": Aggregate.COUNT,
        "field_null_rate": Aggregate.NULL_COUNT,
        "field_unique_rate": Aggregate.DISTINCT_COUNT,
        "field_range": Aggregate.MAX_NUMERIC,
        "validation": Aggregate.COUNT,
        "custom_sql_aggregate": Aggregate.COUNT,
    }

    def __init__(self, executor, monitor_type: str):
        self.executor = executor
        self.monitor_type = monitor_type

    def validate(self, target, budget):
        return CapabilityState.SUPPORTED if self.monitor_type in self.OPERATIONS else CapabilityState.UNSUPPORTED

    def observe(self, tenant_id, environment, target, budget: ProviderBudget) -> ProviderResult:
        operation = self.OPERATIONS.get(self.monitor_type)
        if operation is None:
            return ProviderResult(
                CapabilityState.UNSUPPORTED, missing_data=True, missing_inputs=("provider_not_implemented",)
            )
        columns = target.get("columns") or []
        expression = AggregateExpression(
            operation,
            target.get("schema_name") or "public",
            target.get("table_name") or "",
            columns[0] if columns else target.get("timestamp_column"),
            10_000 if operation == Aggregate.DISTINCT_COUNT else None,
        )
        result = self.executor.execute(expression)
        if self.monitor_type == "freshness" and result.value is not None:
            return replace(result, value=max(0.0, datetime.now(timezone.utc).timestamp() - result.value))
        return result
