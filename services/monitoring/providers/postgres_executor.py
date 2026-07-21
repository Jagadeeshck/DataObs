"""Read-only execution boundary for the reviewed aggregate AST."""

from __future__ import annotations

from contextlib import closing

from services.monitoring.providers.base import CapabilityState, ProviderResult
from services.monitoring.providers.postgres_aggregate import AggregateExpression, compile_expression


class PostgresAggregateExecutor:
    def __init__(self, connect, *, allowed_relations: dict[str, set[str]], statement_timeout_ms: int = 5000):
        self._connect = connect
        self._allowed = allowed_relations
        self._timeout = min(max(statement_timeout_ms, 100), 30_000)

    def execute(self, expression: AggregateExpression) -> ProviderResult:
        relation = f"{expression.schema}.{expression.table}"
        allowed = self._allowed.get(relation)
        if allowed is None or (expression.column and expression.column not in allowed):
            return ProviderResult(
                CapabilityState.PERMISSION_LIMITED, missing_data=True, missing_inputs=("aggregate_not_allowlisted",)
            )
        statement = compile_expression(expression)
        try:
            with closing(self._connect()) as connection, closing(connection.cursor()) as cursor:
                connection.autocommit = False
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET LOCAL statement_timeout = %s", (self._timeout,))
                cursor.execute(statement)
                row = cursor.fetchone()
                connection.rollback()
            value = row[0] if row else None
            return ProviderResult(
                CapabilityState.SUPPORTED,
                value=float(value) if value is not None else None,
                sample_count=1,
                source_coverage=1,
                confidence=1,
                missing_data=value is None,
            )
        except Exception:
            return ProviderResult(
                CapabilityState.TEMPORARILY_UNAVAILABLE,
                missing_data=True,
                missing_inputs=("postgres_aggregate_failed",),
            )
