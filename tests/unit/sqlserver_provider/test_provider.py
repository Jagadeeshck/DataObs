import sys
import types

import pytest

from integrations.database import FixedStatementRegistry, Statement
from integrations.databases.sqlserver.authentication import authentication_options
from integrations.databases.sqlserver.compatibility import validate_product
from integrations.databases.sqlserver.configuration import parse_configuration
from integrations.databases.sqlserver.connection import SqlServerConnectionFactory, build_connection_string
from integrations.databases.sqlserver.evidence import safe_evidence, schema_fingerprint
from integrations.databases.sqlserver.freshness import freshness_statement
from integrations.databases.sqlserver.normalisation import canonical_type
from integrations.databases.sqlserver.profiling import profiling_statement
from integrations.databases.sqlserver.sql import REGISTRY
from packages.collectors.sdk import Capability
from services.collection_manager.cli import build_registry


def config(auth=None, tls=None, **updates):
    value = {
        "host": "sql.internal",
        "database": "app",
        "authentication": auth or {"type": "sql_password", "username": "collector", "password_ref": "env:SQL_PASSWORD"},
        "tls": tls or {"mode": "strict", "trust_server_certificate": False},
    }
    value.update(updates)
    return value


def test_registration_version_and_capabilities():
    provider = build_registry().create("sqlserver")
    assert (provider.provider_type, provider.provider_version) == ("sqlserver", "1")
    assert Capability.QUERY_HISTORY in provider.capabilities().unsupported


@pytest.mark.parametrize(
    "bad",
    [
        {"unknown": True},
        {"connection_string": "x"},
        {"authentication": {"type": "ActiveDirectoryInteractive"}},
        {"authentication": {"type": "sql_password", "username": "u", "password": "inline"}},
        {"tls": {"mode": "optional", "trust_server_certificate": False}},
        {"tls": {"mode": "strict", "trust_server_certificate": True}},
    ],
)
def test_closed_configuration_rejects_unsafe_options(bad):
    value = config()
    value.update(bad)
    with pytest.raises(ValueError):
        parse_configuration(value)


def test_authentication_modes_and_tls(monkeypatch):
    monkeypatch.setenv("SQL_PASSWORD", "secret")
    sql = parse_configuration(config())
    assert authentication_options(sql) == {"UID": "collector", "PWD": "secret"}
    assert "Encrypt={Strict}" in build_connection_string(
        sql
    ) and "TrustServerCertificate={no}" in build_connection_string(sql)
    msi = parse_configuration(config(auth={"type": "entra_managed_identity"}))
    assert authentication_options(msi) == {"Authentication": "ActiveDirectoryMSI"}
    monkeypatch.setenv("SP_SECRET", "secret")
    sp = parse_configuration(
        config(
            auth={"type": "entra_service_principal", "client_id": "id", "client_secret_ref": "env:SP_SECRET"},
            tls={"mode": "mandatory", "trust_server_certificate": False},
        )
    )
    assert authentication_options(sp)["Authentication"] == "ActiveDirectoryServicePrincipal"
    assert "Encrypt={Mandatory}" in build_connection_string(sp)


def test_pooling_disabled_and_connection_closed(monkeypatch):
    calls = []

    class Connection:
        def close(self):
            calls.append("closed")

    module = types.ModuleType("mssql_python")
    module.pooling = lambda enabled: calls.append(enabled)
    module.connect = lambda string, autocommit: (calls.append((string, autocommit)) or Connection())
    monkeypatch.setitem(sys.modules, "mssql_python", module)
    monkeypatch.setenv("SQL_PASSWORD", "secret")
    with SqlServerConnectionFactory().connect(parse_configuration(config())):
        pass
    assert calls[0] is False and calls[-1] == "closed" and calls[1][1] is True


def test_product_vector_normalisation_and_feature_registry():
    assert validate_product("17.0.4065.4") == 17 and validate_product("16.0.4265.3") == 16
    with pytest.raises(RuntimeError):
        validate_product("15.0.1")
    assert canonical_type("vector") == "vector" and canonical_type("uniqueidentifier") == "uuid"
    assert "vector_dimensions" in REGISTRY.get("columns_2025").sql
    assert "vector_dimensions" not in REGISTRY.get("columns_2022").sql


def test_catalog_sql_is_structural_and_private():
    joined = " ".join(
        REGISTRY.get(x).sql
        for x in (
            "identity",
            "schemas",
            "relations",
            "columns_2022",
            "columns_2025",
            "constraints",
            "indexes",
            "partitions",
        )
    ).upper()
    for forbidden in (
        "SELECT *",
        "FILTER_DEFINITION",
        "CHECK_CONSTRAINTS.DEFINITION",
        "DEFAULT_CONSTRAINTS.DEFINITION",
        "QUERY_STORE",
        "SQL_MODULES",
        "OBJECT_DEFINITION",
        "SYS.DATABASES",
    ):
        assert forbidden not in joined
    assert safe_evidence({"column": "x", "definition": "secret", "filter_definition": "secret"}) == {"column": "x"}


def test_fixed_registry_rejects_sqlserver_mutations():
    for sql in ("EXEC dbo.p", "DBCC CHECKDB", "BACKUP DATABASE x", "SELECT * FROM OPENROWSET(x)"):
        with pytest.raises(ValueError):
            FixedStatementRegistry((Statement("bad", sql, 1),))


def test_aggregate_policy_identifier_safety_and_fingerprint():
    assert (
        freshness_statement(
            {"schema": "sales", "table": "orders", "column": "updated_at", "method": "timestamp_column_max"}
        )
        == "SELECT MAX([updated_at]) AS maximum_timestamp FROM [sales].[orders]"
    )
    assert "COUNT(*)" in profiling_statement({"schema": "sales", "table": "orders", "metrics": ["count"]})
    with pytest.raises(ValueError):
        profiling_statement({"schema": "s", "table": "t", "metrics": ["sample"]})
    assert schema_fingerprint([{"table": "t", "approximate_rows": 1}]) == schema_fingerprint(
        [{"table": "t", "approximate_rows": 99}]
    )


@pytest.mark.parametrize("version", ["17", "16"])
def test_live_sqlserver_contract_is_opt_in(version):
    import os

    if os.getenv("RUN_SQLSERVER_INTEGRATION_TESTS") != "1":
        pytest.skip("RUN_SQLSERVER_INTEGRATION_TESTS=1 required")
    assert os.getenv(f"SQLSERVER_{version}_HOST")
