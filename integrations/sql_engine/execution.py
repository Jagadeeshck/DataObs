from dataclasses import dataclass
from time import monotonic
from typing import Any

from .safety import FixedStatementRegistry


@dataclass(frozen=True)
class ExecutionResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    truncated: bool


class BoundedExecutor:
    def __init__(self, registry: FixedStatementRegistry, *, fetch_size: int, maximum_rows: int, maximum_pages: int):
        if not 1 <= fetch_size <= maximum_rows or maximum_pages < 1:
            raise ValueError("invalid execution bounds")
        self.registry, self.fetch_size, self.maximum_rows, self.maximum_pages = (
            registry,
            fetch_size,
            maximum_rows,
            maximum_pages,
        )

    def execute(self, connection, statement_name: str, parameters=None, *, deadline_seconds: float) -> ExecutionResult:
        statement = self.registry.get(statement_name)
        cursor = connection.cursor()
        rows: list[tuple[Any, ...]] = []
        pages = 0
        started = monotonic()
        try:
            cursor.execute(statement.sql, parameters or {})
            columns = tuple(item[0] for item in (cursor.description or ()))
            truncated = False
            while pages < self.maximum_pages and len(rows) < self.maximum_rows:
                if monotonic() - started >= deadline_seconds:
                    if hasattr(cursor, "cancel"):
                        cursor.cancel()
                    raise TimeoutError("statement deadline exceeded")
                batch = cursor.fetchmany(min(self.fetch_size, self.maximum_rows - len(rows)))
                if not batch:
                    return ExecutionResult(columns, tuple(tuple(x) for x in rows), False)
                rows.extend(batch)
                pages += 1
            truncated = bool(cursor.fetchmany(1))
            return ExecutionResult(columns, tuple(tuple(x) for x in rows), truncated)
        finally:
            cursor.close()
