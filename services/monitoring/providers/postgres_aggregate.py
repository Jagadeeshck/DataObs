"""Validated expression compiler for aggregate-only PostgreSQL monitoring.

This module intentionally does not accept SQL text.  Callers select one reviewed
operation and identifiers are quoted only after a conservative validation step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


class Aggregate(str, Enum):
    COUNT = "count"
    MAX_TIMESTAMP = "max_timestamp"
    MIN_NUMERIC = "min_numeric"
    MAX_NUMERIC = "max_numeric"
    NULL_COUNT = "null_count"
    ZERO_COUNT = "zero_count"
    NEGATIVE_COUNT = "negative_count"
    DISTINCT_COUNT = "distinct_count"


@dataclass(frozen=True)
class AggregateExpression:
    operation: Aggregate
    schema: str
    table: str
    column: str | None = None
    distinct_limit: int | None = None


def quote_identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError("unsafe PostgreSQL identifier")
    return f'"{value}"'


def compile_expression(expression: AggregateExpression, *, maximum_distinct: int = 10_000) -> str:
    relation = f"{quote_identifier(expression.schema)}.{quote_identifier(expression.table)}"
    if expression.operation == Aggregate.COUNT:
        return f"SELECT /* dataobs-monitor */ COUNT(*) FROM {relation}"
    if expression.column is None:
        raise ValueError("aggregate requires a column")
    column = quote_identifier(expression.column)
    fragments = {
        Aggregate.MAX_TIMESTAMP: f"MAX({column})",
        Aggregate.MIN_NUMERIC: f"MIN({column})",
        Aggregate.MAX_NUMERIC: f"MAX({column})",
        Aggregate.NULL_COUNT: f"COUNT(*) FILTER (WHERE {column} IS NULL)",
        Aggregate.ZERO_COUNT: f"COUNT(*) FILTER (WHERE {column} = 0)",
        Aggregate.NEGATIVE_COUNT: f"COUNT(*) FILTER (WHERE {column} < 0)",
        Aggregate.DISTINCT_COUNT: f"COUNT(DISTINCT {column})",
    }
    if expression.operation == Aggregate.DISTINCT_COUNT:
        if expression.distinct_limit is None or not 1 <= expression.distinct_limit <= maximum_distinct:
            raise ValueError("bounded distinct_limit is required")
    return f"SELECT /* dataobs-monitor */ {fragments[expression.operation]} FROM {relation}"
