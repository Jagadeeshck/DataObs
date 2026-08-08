import re
from dataclasses import dataclass

_MUTATION = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|CALL|EXECUTE|PREPARE|REFRESH)\b|\bSET\s+(?:ROLE|SESSION\s+AUTHORIZATION)\b",
    re.I,
)
_PASSTHROUGH = re.compile(r"system\s*\.\s*query\s*\(|system\.runtime\.kill_query", re.I)
_ALLOWED_START = re.compile(r"^\s*(?:SELECT|SHOW|DESCRIBE)\b", re.I)


@dataclass(frozen=True)
class FixedStatement:
    name: str
    sql: str
    family: str


def validate_read_only_statement(sql: str) -> None:
    if not _ALLOWED_START.search(sql) or _MUTATION.search(sql) or _PASSTHROUGH.search(sql):
        raise ValueError("statement is not an allowed read-only form")
    if re.search(r"\bSELECT\s+\*", sql, re.I):
        raise ValueError("SELECT * is prohibited")
    if ";" in sql or "--" in sql or "/*" in sql:
        raise ValueError("comments and multiple statements are prohibited")


class FixedStatementRegistry:
    """Closed registry: callers select a name, never provide SQL."""

    def __init__(self, statements: tuple[FixedStatement, ...]):
        self._statements: dict[str, FixedStatement] = {}
        for statement in statements:
            validate_read_only_statement(statement.sql)
            if statement.name in self._statements:
                raise ValueError("duplicate statement")
            self._statements[statement.name] = statement

    def get(self, name: str) -> FixedStatement:
        try:
            return self._statements[name]
        except KeyError as exc:
            raise KeyError("unknown fixed statement") from exc

    def all(self) -> tuple[FixedStatement, ...]:
        return tuple(self._statements.values())
