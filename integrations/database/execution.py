from __future__ import annotations


class BoundedStatementExecutor:
    """Executes only registered provider-owned statements and bounds returned metadata."""

    def __init__(self, registry, maximum_rows: int):
        self.registry, self.maximum_rows = registry, maximum_rows

    def execute(self, connection, statement_id: str, parameters=()):
        statement = self.registry.get(statement_id)
        limit = min(statement.maximum_rows, self.maximum_rows)
        with connection.cursor() as cursor:
            try:
                cursor.execute(statement.sql, parameters)
                columns = [getattr(c, "name", c[0]) for c in cursor.description]
                rows = cursor.fetchmany(limit + 1)
                return [dict(zip(columns, row)) for row in rows[:limit]], len(rows) > limit
            except Exception:
                if hasattr(connection, "rollback"):
                    connection.rollback()
                raise
