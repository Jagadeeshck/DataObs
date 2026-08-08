import pytest

from integrations.sql_engine import BoundedExecutor, FixedStatement, FixedStatementRegistry, quote_identifier


class Cursor:
    description = (("value",),)

    def __init__(self, rows):
        self.rows = list(rows)
        self.closed = False
        self.cancelled = False

    def execute(self, sql, params):
        self.sql = sql

    def fetchmany(self, n):
        out = self.rows[:n]
        self.rows = self.rows[n:]
        return out

    def close(self):
        self.closed = True

    def cancel(self):
        self.cancelled = True


class Connection:
    def __init__(self, rows):
        self.c = Cursor(rows)

    def cursor(self):
        return self.c


def test_fixed_registry_and_bounded_fetch_closes_cursor():
    registry = FixedStatementRegistry((FixedStatement("safe", "SELECT 1 AS value", "health"),))
    connection = Connection([(1,), (2,), (3,)])
    result = BoundedExecutor(registry, fetch_size=1, maximum_rows=2, maximum_pages=2).execute(
        connection, "safe", deadline_seconds=10
    )
    assert result.rows == ((1,), (2,)) and result.truncated and connection.c.closed


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM system.runtime.nodes",
        "DELETE FROM x",
        "CALL x()",
        "SELECT a FROM TABLE(x.system.query('x'))",
        "SELECT a FROM x; DROP TABLE x",
    ],
)
def test_unsafe_statements_rejected(sql):
    with pytest.raises(ValueError):
        FixedStatementRegistry((FixedStatement("bad", sql, "x"),))


@pytest.mark.parametrize("identifier", ["x;drop", "x--comment", 'bad"quote', "x\x00y"])
def test_identifier_injection_rejected(identifier):
    with pytest.raises(ValueError):
        quote_identifier(identifier)


def test_identifier_quotes_legitimate_name():
    assert quote_identifier("Sales Data") == '"Sales Data"'
