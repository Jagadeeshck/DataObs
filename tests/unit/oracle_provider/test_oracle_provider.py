import pytest

from integrations.database import FixedStatementRegistry, Statement
from integrations.databases.oracle.configuration import parse_configuration
from integrations.databases.oracle.dialect import quote_identifier
from integrations.databases.oracle.evidence import safe_evidence, schema_fingerprint
from integrations.databases.oracle.freshness import freshness_statement
from integrations.databases.oracle.normalisation import canonical_type
from integrations.databases.oracle.profiling import profiling_statement
from integrations.databases.oracle.provider import OracleDatabaseProvider
from integrations.databases.oracle.sql import REGISTRY
from services.collection_manager.cli import build_registry

BASE = {
    "host": "db.example",
    "service_name": "APPPDB",
    "authentication": {"type": "password", "username": "COLLECTOR", "password_ref": "env:PW"},
    "tls": {"enabled": True, "protocol": "tcps", "verify_server_identity": True},
}


def test_registration_identity_capabilities():
    p = OracleDatabaseProvider()
    assert (p.provider_type, p.provider_version) == ("oracle", "1")
    assert "oracle" in build_registry().provider_types()
    assert any(x.value == "query_history" for x in p.capabilities().unsupported)


def test_closed_configuration_and_inline_secret():
    parse_configuration(BASE)
    with pytest.raises(ValueError):
        parse_configuration({**BASE, "dsn": "x"})
    with pytest.raises(ValueError):
        parse_configuration({**BASE, "authentication": {"type": "password", "username": "U", "password": "plain"}})


def test_tls_and_privileged_auth_fail_closed():
    with pytest.raises(ValueError):
        parse_configuration({**BASE, "tls": {"enabled": False}})
    with pytest.raises(ValueError):
        parse_configuration({**BASE, "authentication": {"type": "SYSDBA", "username": "U", "password_ref": "env:PW"}})


def test_service_and_identifier_injection_rejected():
    with pytest.raises(ValueError):
        parse_configuration({**BASE, "service_name": "x)(DESCRIPTION="})
    with pytest.raises(ValueError):
        quote_identifier('X" FROM secrets')


def test_sql_is_fixed_safe_and_private():
    for name in (
        "identity",
        "schemas",
        "tables",
        "views",
        "materialized_views",
        "columns",
        "vector_columns",
        "constraints",
        "indexes",
        "partitions",
    ):
        REGISTRY.get(name)
    sql = " ".join(
        REGISTRY.get(x).sql for x in ("views", "materialized_views", "columns", "constraints", "indexes", "partitions")
    ).upper()
    for forbidden in (
        "DATA_DEFAULT",
        "LOW_VALUE",
        "HIGH_VALUE",
        "SEARCH_CONDITION",
        "ALL_IND_EXPRESSIONS",
        "DBA_",
        "V$SQL",
        "DBA_HIST",
        "DBMS_VECTOR",
        "SELECT *",
    ):
        assert forbidden not in sql


def test_oracle_mutation_and_plsql_rejected():
    for sql in (
        "SELECT 1 FROM dual; COMMIT",
        "BEGIN NULL; END;",
        "SELECT DBMS_STATS.X FROM dual",
        "ALTER SESSION SET X=1",
        "LOCK TABLE x IN EXCLUSIVE MODE",
    ):
        with pytest.raises(ValueError):
            FixedStatementRegistry((Statement("bad", sql, 1),))


def test_type_normalisation():
    assert canonical_type("NUMBER") == "decimal"
    assert canonical_type("TIMESTAMP WITH TIME ZONE").startswith("timestamp")
    assert canonical_type("VECTOR") == "vector"
    assert canonical_type("MY_OBJECT") == "other"


def test_sensitive_evidence_and_fingerprint():
    row = {"column": "C", "data_default": "secret", "low_value": b"x", "search_condition": "x>1"}
    assert safe_evidence(row) == {"column": "C"}
    assert schema_fingerprint([{"column": "C", "num_rows": 1}]) == schema_fingerprint([{"column": "C", "num_rows": 2}])


def test_freshness_is_policy_owned():
    assert (
        freshness_statement(
            {"method": "timestamp_column_max", "schema": "SALES", "table": "ORDERS", "column": "UPDATED_AT"}
        )
        == 'SELECT MAX("UPDATED_AT") AS maximum_timestamp FROM "SALES"."ORDERS"'
    )
    with pytest.raises(ValueError):
        freshness_statement({"method": "sql", "schema": "S", "table": "T", "column": "C"})


def test_profiling_aggregate_only():
    sql = profiling_statement(
        {"schema": "S", "table": "T", "column": "C", "metrics": ["count", "null_count", "distinct_count", "min_length"]}
    )
    assert sql.startswith("SELECT COUNT(")
    assert " FROM " in sql
    with pytest.raises(ValueError):
        profiling_statement({"schema": "S", "table": "T", "metrics": ["sample"]})


def test_thin_dependency_is_optional(monkeypatch):
    import builtins

    from integrations.databases.oracle.connection import OracleConnectionFactory

    real = builtins.__import__
    monkeypatch.setattr(
        builtins,
        "__import__",
        lambda n, *a, **k: (_ for _ in ()).throw(ImportError()) if n == "oracledb" else real(n, *a, **k),
    )
    with pytest.raises(RuntimeError, match="dependency_unavailable"):
        with OracleConnectionFactory().connect(parse_configuration(BASE)):
            pass
