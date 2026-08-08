from __future__ import annotations

import re
from dataclasses import dataclass

_MUTATION = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|COPY|CALL|DO|VACUUM|ANALYZE|REINDEX|GRANT|REVOKE|SECURITY\s+LABEL|SET\s+ROLE|SESSION\s+AUTHORIZATION)\b",
    re.I,
)


@dataclass(frozen=True)
class Statement:
    identifier: str
    sql: str
    maximum_rows: int


class FixedStatementRegistry:
    def __init__(self, statements):
        self._statements = {s.identifier: s for s in statements}
        if len(self._statements) != len(tuple(statements)):
            raise ValueError("duplicate statement identifier")
        for statement in self._statements.values():
            if _MUTATION.search(statement.sql) or not statement.sql.lstrip().upper().startswith(("SELECT", "WITH")):
                raise ValueError("unsafe provider statement")

    def get(self, identifier: str) -> Statement:
        try:
            return self._statements[identifier]
        except KeyError as exc:
            raise ValueError("unknown provider statement") from exc
