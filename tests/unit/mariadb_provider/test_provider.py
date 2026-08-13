import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from integrations.database.schema import structural_fingerprint
from integrations.databases.mariadb.compatibility import validate_product
from integrations.databases.mariadb.configuration import parse_configuration
from integrations.databases.mariadb.connection import MariaDbConnectionFactory
from integrations.databases.mariadb.evidence import safe_evidence, schema_fingerprint
from integrations.databases.mariadb.freshness import freshness_statement
from integrations.databases.mariadb.normalisation import canonical_type
from integrations.databases.mariadb.profiling import profiling_statement
from integrations.databases.mariadb.provider import MariaDbDatabaseProvider
from integrations.databases.mariadb.sql import REGISTRY
from packages.collectors.sdk import Capability, IntegrationContext, PartialFailure, ResourceObservation
from services.collection_manager.cli import build_registry


def config(**updates):
    value = {
        "host": "mariadb.internal",
        "database": "app",
        "authentication": {"type": "password", "username": "collector", "password_ref": "env:MARIADB_PASSWORD"},
        "tls": {
            "enabled": True,
            "verify_certificate": True,
            "verify_identity": True,
            "ca_bundle_ref": "file-ref:/ca.pem",
        },
    }
    value.update(updates)
    return value


def test_registration_capabilities_and_version():
    registry = build_registry()
    assert registry.provider_types() == (
        "aws",
        "azure",
        "bigquery",
        "databricks",
        "mariadb",
        "mysql",
        "oracle",
        "postgres",
        "presto",
        "snowflake",
        "sqlserver",
        "trino",
    )
    provider = registry.create("mariadb")
    assert (provider.provider_type, provider.provider_version) == ("mariadb", "1")
    assert Capability.QUERY_HISTORY not in provider.capabilities().supported


def test_closed_configuration_secrets_and_tls():
    assert parse_configuration(config()).port == 3306
    for bad in (
        {"unknown": True},
        {"authentication": {"type": "password", "username": "u", "password": "plaintext"}},
        {
            "tls": {
                "enabled": True,
                "verify_certificate": False,
                "verify_identity": True,
                "ca_bundle_ref": "file-ref:/ca",
            }
        },
        {"host": "mariadb://u:p@host/db"},
    ):
        value = config()
        value.update(bad)
        with pytest.raises(ValueError):
            parse_configuration(value)


def test_connector_options_enforce_tls_identity_and_local_infile(monkeypatch):
    captured = {}

    class Connection:
        def close(self):
            pass

    class Connector:
        def connect(self, **kwargs):
            captured.update(kwargs)
            return Connection()

    import sys
    import types

    package = types.ModuleType("mariadb")
    package.connect = Connector().connect
    monkeypatch.setitem(sys.modules, "mariadb", package)
    monkeypatch.setenv("MARIADB_PASSWORD", "secret")
    cfg = parse_configuration(config())
    with MariaDbConnectionFactory().connect(cfg):
        pass
    assert captured["ssl_verify_cert"] is True and captured["ssl_ca"] == "/ca.pem"
    assert captured["local_infile"] is False
    assert "ssl_verify_identity" not in captured  # Connector/C performs identity verification with certificate verify.
    assert "password" in captured and captured["password"] == "secret"


def test_product_detection_and_mysql_mismatch():
    assert validate_product("11.8.2-MariaDB", "MariaDB Community Server") == "11.8"
    assert validate_product("11.4.8-MariaDB", "MariaDB") == "11.4"
    with pytest.raises(RuntimeError, match="server_product_mismatch"):
        validate_product("8.4.10", "MySQL Community Server")


def test_safe_fixed_sql_and_no_raw_rows_or_query_text():
    joined = " ".join(
        REGISTRY.get(name).sql
        for name in ("health", "schemas", "relations", "columns", "constraints", "indexes", "partitions")
    ).upper()
    assert "SELECT *" not in joined
    assert not any(
        term in joined
        for term in (
            "VIEW_DEFINITION",
            "CHECK_CLAUSE",
            "GENERATION_EXPRESSION",
            "PARTITION_EXPRESSION",
            "DIGEST_TEXT",
            "QUERY_SAMPLE_TEXT",
            "SQL_TEXT",
            "ANALYZE TABLE",
            "LOAD DATA",
        )
    )
    row = safe_evidence({"column": "x", "column_default": "secret", "check_clause": "x > 1", "expression": "secret"})
    assert row == {"column": "x"}


@pytest.mark.parametrize(
    ("native", "detail", "expected"),
    [
        ("tinyint", "tinyint(1)", "boolean"),
        ("bigint", "bigint unsigned", "unsigned_integer"),
        ("decimal", "decimal(10,2)", "decimal"),
        ("varchar", "varchar(10)", "string"),
        ("json", "json", "json"),
        ("geometry", "geometry", "spatial"),
        ("vector", "vector(3)", "vector"),
    ],
)
def test_type_normalisation(native, detail, expected):
    assert canonical_type(native, detail) == expected


def test_fingerprint_excludes_dynamic_and_sensitive_values():
    left = [{"schema": "s", "table": "t", "column": "c", "approximate_rows": 1, "column_default": "a"}]
    right = [{"schema": "s", "table": "t", "column": "c", "approximate_rows": 9, "column_default": "b"}]
    assert schema_fingerprint(left) == schema_fingerprint(right)
    assert structural_fingerprint([{"x": 1}]) == structural_fingerprint([{"x": 1}])


def test_freshness_and_profiling_are_generated_aggregate_only():
    assert (
        freshness_statement(
            {"schema": "sales", "table": "orders", "column": "updated_at", "method": "timestamp_column_max"}
        )
        == "SELECT MAX(`updated_at`) AS maximum_timestamp FROM `sales`.`orders`"
    )
    sql = profiling_statement(
        {
            "schema": "sales",
            "table": "orders",
            "column": "id",
            "metrics": ["count", "null_count", "distinct_count", "min", "max"],
        }
    )
    assert "COUNT(*)" in sql and "SELECT *" not in sql and " WHERE " not in sql
    with pytest.raises(ValueError):
        profiling_statement({"schema": "s", "table": "t", "metrics": ["sample"]})


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, parameters=()):
        self.sql = sql
        if "VERSION()" in sql:
            self.description = [("server_version",), ("version_comment",)]
            self.rows = [("11.8.2-MariaDB", "MariaDB Community Server")]
        elif "information_schema.schemata" in sql:
            self.description = [("schema",)]
            self.rows = [("sales",), ("mariadb",)]
        elif "information_schema.tables" in sql:
            self.description = [("schema",), ("table",), ("table_type",), ("engine",), ("approximate_rows",)]
            self.rows = [("sales", "orders", "BASE TABLE", "InnoDB", 12), ("sales", "v", "VIEW", None, None)]
        elif "information_schema.columns" in sql:
            self.description = [("schema",), ("table",), ("column",), ("native_type",), ("column_type",)]
            self.rows = [("sales", "orders", "id", "bigint", "bigint unsigned")]
        elif "information_schema.statistics" in sql and self.connection.fail_indexes:
            raise PermissionError
        else:
            self.description = [("schema",), ("table",)]
            self.rows = []

    def fetchmany(self, count):
        return self.rows[:count]


class Connection:
    def __init__(self, fail_indexes=False):
        self.fail_indexes = fail_indexes
        self.closed = False

    def cursor(self):
        return Cursor(self)

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class Factory:
    def __init__(self, fail_indexes=False):
        self.connection = Connection(fail_indexes)

    def connect(self, cfg):
        outer = self

        class CM:
            def __enter__(self):
                return outer.connection

            def __exit__(self, *args):
                outer.connection.close()

        return CM()


def test_collection_structural_evidence_partial_failure_and_isolation():
    factory = Factory(True)
    provider = MariaDbDatabaseProvider(factory)
    context = IntegrationContext(
        "tenant-a",
        "mariadb-a",
        "run",
        datetime.now(timezone.utc) + timedelta(seconds=30),
        attributes={"environment": "prod"},
    )
    assert asyncio.run(
        provider.validate_configuration(
            context,
            config(discovery={"exclude_schemas": ["mariadb", "information_schema", "performance_schema", "sys"]}),
        )
    ).valid
    request = type("Request", (), {"capabilities": frozenset({Capability.METADATA_COLLECTION})})()
    results = asyncio.run(_collect(provider, context, request))
    observations = [x for x in results if isinstance(x, ResourceObservation)]
    assert observations and all(x.provider == "mariadb" and x.region == "prod" for x in observations)
    assert all(x.source_evidence["raw_rows_persisted"] is False for x in observations)
    assert any(isinstance(x, PartialFailure) and x.error_code == "metadata_unavailable" for x in results)
    assert factory.connection.closed
    other = DatabaseIdentityForTest("tenant-b", "dev")
    assert observations[0].native_resource_id != other


async def _collect(provider, context, request):
    return [item async for item in provider.collect(context, request)]


def DatabaseIdentityForTest(tenant, environment):
    from integrations.database import DatabaseIdentity

    return DatabaseIdentity(tenant, environment, "mariadb", "mariadb-a", "instance", "app").canonical_id()


def test_live_mariadb_contract_is_opt_in():
    import os

    if os.getenv("RUN_MARIADB_INTEGRATION_TESTS") != "1":
        pytest.skip("RUN_MARIADB_INTEGRATION_TESTS=1 required")
    assert os.getenv("MARIADB_HOST"), "live test requires synthetic MariaDB fixture configuration"
