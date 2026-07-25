"""
Tests for DataObs quality check modules.

Covers:
  - NullCheck
  - RowCountCheck (including anomaly detection path)
  - UniquenessCheck
  - ValueRangeCheck
  - ReferentialIntegrityCheck
  - SchemaCheck
"""

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from src.quality.checks.null_check import NullCheck  # noqa: E402
from src.quality.checks.referential_integrity_check import ReferentialIntegrityCheck  # noqa: E402
from src.quality.checks.row_count_check import RowCountCheck  # noqa: E402
from src.quality.checks.schema_check import SchemaCheck  # noqa: E402
from src.quality.checks.uniqueness_check import UniquenessCheck  # noqa: E402
from src.quality.checks.value_range_check import ValueRangeCheck  # noqa: E402

# ---------------------------------------------------------------------------
# Fake ES client for SchemaCheck (stores and retrieves schema baselines)
# ---------------------------------------------------------------------------


class _FakeSchemaES:
    """Minimal ES stub for SchemaCheck._get_stored_schema / _store_schema."""

    def __init__(self, stored_schema=None):
        # stored_schema: dict of {column: type} or None for first-run
        self._stored = stored_schema
        self.indexed_docs = []

    def search(self, index, **kwargs):
        if self._stored is None:
            return {"hits": {"hits": []}}
        return {"hits": {"hits": [{"_source": {"schema": self._stored}}]}}

    def index(self, index, document, **kwargs):
        self.indexed_docs.append(document)
        self._stored = document.get("schema", {})


# ---------------------------------------------------------------------------
# Fake ES client — accepts keyword-argument API (elasticsearch-py 8.x style)
# ---------------------------------------------------------------------------


class _FakeES:
    def __init__(self, metric_values):
        self.metric_values = metric_values

    def search(self, index, **kwargs):  # was: def search(self, index, body)
        hits = [{"_source": {"metric_value": v}} for v in self.metric_values]
        return {"hits": {"hits": hits}}


# ---------------------------------------------------------------------------
# Shared DB helpers
# ---------------------------------------------------------------------------


def _db_with_orders(rows):
    engine = sqlalchemy.create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("CREATE TABLE orders (order_id INTEGER, customer_id INTEGER, total_amount REAL)"))
        for row in rows:
            conn.execute(
                sqlalchemy.text(
                    "INSERT INTO orders(order_id, customer_id, total_amount) "
                    "VALUES (:order_id, :customer_id, :total_amount)"
                ),
                row,
            )
        conn.commit()
    return engine


def _db_with_orders_and_customers(order_rows, customer_rows):
    """DB with both orders and customers tables for referential integrity tests."""
    engine = sqlalchemy.create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("CREATE TABLE orders (order_id INTEGER, customer_id INTEGER)"))
        conn.execute(sqlalchemy.text("CREATE TABLE customers (id INTEGER PRIMARY KEY)"))
        for row in order_rows:
            conn.execute(
                sqlalchemy.text("INSERT INTO orders VALUES (:order_id, :customer_id)"),
                row,
            )
        for row in customer_rows:
            conn.execute(
                sqlalchemy.text("INSERT INTO customers VALUES (:id)"),
                row,
            )
        conn.commit()
    return engine


# ===========================================================================
# NullCheck
# ===========================================================================


def test_null_check_fails_when_null_pct_exceeds_threshold():
    engine = _db_with_orders(
        [
            {"order_id": 1, "customer_id": 10, "total_amount": 5.0},
            {"order_id": 2, "customer_id": None, "total_amount": 3.0},
            {"order_id": 3, "customer_id": None, "total_amount": 1.0},
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


def test_null_check_passes_when_within_threshold():
    engine = _db_with_orders(
        [
            {"order_id": 1, "customer_id": 10, "total_amount": 5.0},
            {"order_id": 2, "customer_id": 20, "total_amount": 3.0},
        ]
    )
    check = NullCheck()
    result = check.run(
        {
            "dataset": "prod.public.orders",
            "columns": ["customer_id"],
            "max_null_pct": 0.0,
            "severity": "critical",
        },
        engine,
    )

    assert result.status == "PASS"


# ===========================================================================
# RowCountCheck — basic bounds
# ===========================================================================


def test_row_count_check_passes_within_bounds():
    engine = _db_with_orders([{"order_id": i, "customer_id": i, "total_amount": float(i)} for i in range(50)])
    check = RowCountCheck()
    result = check.run(
        {"dataset": "prod.public.orders", "min_rows": 10, "max_rows": 100, "severity": "high"},
        engine,
    )
    assert result.status == "PASS"


def test_row_count_check_fails_below_minimum():
    engine = _db_with_orders([{"order_id": 1, "customer_id": 1, "total_amount": 1.0}])
    check = RowCountCheck()
    result = check.run(
        {"dataset": "prod.public.orders", "min_rows": 100, "severity": "high"},
        engine,
    )
    assert result.status == "FAIL"


# ===========================================================================
# RowCountCheck — anomaly detection (was deselected due to mock bug, now fixed)
# ===========================================================================


def test_row_count_check_anomaly_detection_flags_large_outlier():
    engine = _db_with_orders([{"order_id": i, "customer_id": i, "total_amount": float(i)} for i in range(1000)])
    # Historical baseline ≈ 100 rows, std ≈ 2 → 1000 rows is many std devs above mean
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


def test_row_count_check_anomaly_detection_passes_within_baseline():
    """Row count within 1 std-dev of historical mean should pass anomaly check."""
    engine = _db_with_orders([{"order_id": i, "customer_id": i, "total_amount": float(i)} for i in range(100)])
    # Historical baseline ≈ 100, std ≈ 2 — 100 rows is exactly on the mean
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

    assert result.status == "PASS"


# ===========================================================================
# UniquenessCheck
# ===========================================================================


def test_uniqueness_check_fails_on_duplicates():
    engine = _db_with_orders(
        [
            {"order_id": 1, "customer_id": 10, "total_amount": 5.0},
            {"order_id": 1, "customer_id": 20, "total_amount": 3.0},  # duplicate order_id
            {"order_id": 3, "customer_id": 30, "total_amount": 1.0},
        ]
    )
    check = UniquenessCheck()
    result = check.run(
        {"dataset": "prod.public.orders", "columns": ["order_id"], "severity": "critical"},
        engine,
    )
    assert result.status == "FAIL"


def test_uniqueness_check_passes_on_unique_column():
    engine = _db_with_orders(
        [
            {"order_id": 1, "customer_id": 10, "total_amount": 5.0},
            {"order_id": 2, "customer_id": 20, "total_amount": 3.0},
        ]
    )
    check = UniquenessCheck()
    result = check.run(
        {"dataset": "prod.public.orders", "columns": ["order_id"], "severity": "critical"},
        engine,
    )
    assert result.status == "PASS"


# ===========================================================================
# ValueRangeCheck
# ===========================================================================


def test_value_range_check_fails_on_out_of_range():
    engine = _db_with_orders(
        [
            {"order_id": 1, "customer_id": 10, "total_amount": -50.0},  # negative — below min
            {"order_id": 2, "customer_id": 20, "total_amount": 5.0},
        ]
    )
    check = ValueRangeCheck()
    result = check.run(
        {
            "dataset": "prod.public.orders",
            "column": "total_amount",
            "min_value": 0,
            "max_value": 1000000,
            "severity": "high",
        },
        engine,
    )
    assert result.status == "FAIL"


def test_value_range_check_passes_within_range():
    engine = _db_with_orders(
        [
            {"order_id": 1, "customer_id": 10, "total_amount": 100.0},
            {"order_id": 2, "customer_id": 20, "total_amount": 250.0},
        ]
    )
    check = ValueRangeCheck()
    result = check.run(
        {
            "dataset": "prod.public.orders",
            "column": "total_amount",
            "min_value": 0,
            "max_value": 1000000,
            "severity": "high",
        },
        engine,
    )
    assert result.status == "PASS"


# ===========================================================================
# ReferentialIntegrityCheck
# ===========================================================================


def test_referential_integrity_fails_on_orphaned_rows():
    engine = _db_with_orders_and_customers(
        order_rows=[
            {"order_id": 1, "customer_id": 10},
            {"order_id": 2, "customer_id": 999},  # 999 does not exist in customers
        ],
        customer_rows=[{"id": 10}],
    )
    check = ReferentialIntegrityCheck()
    # references format: "<anything>.<ref_table>.<ref_column>"
    # The check splits on '.' and uses the last part as ref_column,
    # and everything before that as ref_table.
    result = check.run(
        {
            "dataset": "orders",
            "column": "customer_id",
            "references": "customers.id",  # ref_table=customers, ref_column=id
            "severity": "high",
        },
        engine,
    )
    assert result.status == "FAIL"


def test_referential_integrity_passes_on_valid_references():
    engine = _db_with_orders_and_customers(
        order_rows=[
            {"order_id": 1, "customer_id": 10},
            {"order_id": 2, "customer_id": 20},
        ],
        customer_rows=[{"id": 10}, {"id": 20}],
    )
    check = ReferentialIntegrityCheck()
    result = check.run(
        {
            "dataset": "orders",
            "column": "customer_id",
            "references": "customers.id",
            "severity": "high",
        },
        engine,
    )
    assert result.status == "PASS"


# ===========================================================================
# SchemaCheck — tests via _compare_schemas (unit) and first-run baseline
# ===========================================================================


def test_schema_check_compare_detects_column_removed():
    es = _FakeSchemaES(stored_schema={"order_id": "INTEGER", "customer_id": "INTEGER"})
    check = SchemaCheck(es_client=es)
    changes = check._compare_schemas(
        previous={"order_id": "INTEGER", "customer_id": "INTEGER"},
        current={"order_id": "INTEGER"},  # customer_id removed
    )
    removed = [c for c in changes if c["change_type"] == "column_removed"]
    assert len(removed) == 1
    assert removed[0]["column"] == "customer_id"


def test_schema_check_compare_detects_type_changed():
    es = _FakeSchemaES()
    check = SchemaCheck(es_client=es)
    changes = check._compare_schemas(
        previous={"total_amount": "INTEGER"},
        current={"total_amount": "FLOAT"},
    )
    changed = [c for c in changes if c["change_type"] == "type_changed"]
    assert len(changed) == 1
    assert changed[0]["column"] == "total_amount"


def test_schema_check_compare_detects_column_added():
    es = _FakeSchemaES()
    check = SchemaCheck(es_client=es)
    changes = check._compare_schemas(
        previous={"order_id": "INTEGER"},
        current={"order_id": "INTEGER", "new_col": "TEXT"},
    )
    added = [c for c in changes if c["change_type"] == "column_added"]
    assert len(added) == 1
    assert added[0]["column"] == "new_col"


def test_schema_check_first_run_stores_baseline_and_passes():
    """On first run (no stored schema), check should store baseline and return PASS."""
    es = _FakeSchemaES(stored_schema=None)

    class _PatchedSchemaCheck(SchemaCheck):
        """Override _get_current_schema to avoid needing information_schema in SQLite."""

        def _get_current_schema(self, dataset, connection):
            return {"order_id": "INTEGER", "customer_id": "INTEGER"}

    check = _PatchedSchemaCheck(es_client=es)
    result = check.run(
        {"dataset": "prod.public.orders", "alert_on": ["column_removed"], "severity": "critical"},
        connection=None,
    )
    assert result.status == "PASS"
    assert len(es.indexed_docs) == 1  # baseline stored


def test_schema_check_fails_on_column_removed_vs_stored_baseline():
    """Stored baseline has customer_id; current schema dropped it — should FAIL."""
    es = _FakeSchemaES(stored_schema={"order_id": "INTEGER", "customer_id": "INTEGER"})

    class _PatchedSchemaCheck(SchemaCheck):
        def _get_current_schema(self, dataset, connection):
            return {"order_id": "INTEGER"}  # customer_id removed

    check = _PatchedSchemaCheck(es_client=es)
    result = check.run(
        {"dataset": "prod.public.orders", "alert_on": ["column_removed"], "severity": "critical"},
        connection=None,
    )
    assert result.status == "FAIL"


# ===========================================================================
# Registry, SQL safety, and distribution drift extensibility
# ===========================================================================


def test_quality_check_registry_exposes_supported_types():
    from src.quality.checks.registry import build_check, supported_check_types

    assert "row_count" in supported_check_types()
    assert "distribution_drift" in supported_check_types()
    assert build_check("row_count").check_type == "row_count"
    with pytest.raises(ValueError, match="Unsupported check type"):
        build_check("not_a_real_check")


def test_identifier_validation_rejects_sql_fragments():
    from src.quality.checks.sql import table_name_from_dataset, validate_column_names

    assert table_name_from_dataset("prod.public.orders") == "orders"
    assert validate_column_names(["customer_id", "total_amount"]) == ["customer_id", "total_amount"]
    with pytest.raises(ValueError):
        table_name_from_dataset("orders; DROP TABLE orders")
    with pytest.raises(ValueError):
        validate_column_names(["customer_id) IS NULL OR 1=1 --"])


def test_distribution_drift_check_returns_standard_check_result():
    from src.quality.checks.distribution_drift_check import DistributionDriftCheck

    check = DistributionDriftCheck(table="orders", column="total_amount")
    result = check.run([10.0, 11.0, 12.0, 13.0])

    assert result.check_type == "distribution_drift"
    assert result.dataset == "orders"
    assert result.status == "PASS"
    assert result.details["column"] == "total_amount"
    assert result.to_es_doc()["check_type"] == "distribution_drift"
