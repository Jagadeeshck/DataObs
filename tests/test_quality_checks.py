import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from src.quality.checks.null_check import NullCheck
from src.quality.checks.row_count_check import RowCountCheck


class _FakeES:
    def __init__(self, metric_values):
        self.metric_values = metric_values

    def search(self, index, body):
        hits = [{"_source": {"metric_value": v}} for v in self.metric_values]
        return {"hits": {"hits": hits}}


def _db_with_orders(rows):
    engine = sqlalchemy.create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("CREATE TABLE orders (order_id INTEGER, customer_id INTEGER)"))
        for row in rows:
            conn.execute(
                sqlalchemy.text("INSERT INTO orders(order_id, customer_id) VALUES (:order_id, :customer_id)"),
                row,
            )
        conn.commit()
    return engine


def test_null_check_fails_when_null_pct_exceeds_threshold():
    engine = _db_with_orders(
        [
            {"order_id": 1, "customer_id": 10},
            {"order_id": 2, "customer_id": None},
            {"order_id": 3, "customer_id": None},
        ]
    )
    check = NullCheck()
    result = check.run(
        {
            "dataset": "prod.public.orders",
            "columns": ["customer_id"],
            "max_null_pct": 10.0,
            "severity": "critical",
        },
        engine,
    )

    assert result.status == "FAIL"
    assert result.details["violations"]["customer_id"]["null_count"] == 2


def test_row_count_check_anomaly_detection_flags_large_outlier():
    engine = _db_with_orders([{"order_id": i, "customer_id": i} for i in range(1000)])
    es = _FakeES([100, 105, 98, 102, 99, 101, 103, 97, 100])
    check = RowCountCheck(es_client=es)

    result = check.run(
        {
            "dataset": "prod.public.orders",
            "anomaly_detection": True,
            "stddev_threshold": 3.0,
            "severity": "high",
        },
        engine,
    )

    assert result.status == "FAIL"
    assert "z_score" in result.details
