import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from integrations.trino import TrinoSqlEngineProvider
from integrations.trino.configuration import parse_configuration
from integrations.trino.sql import REGISTRY, catalog_registry
from packages.collectors.sdk import Capability, IntegrationContext
from services.collection_manager.cli import build_registry

BASE = {
    "host": "trino.example.internal",
    "port": 8443,
    "authentication": {"type": "basic", "username": "dataobs_collector", "password_ref": "env:SECRET"},
    "tls": {"verify": True},
}


def test_registry_identity_and_capabilities():
    registry = build_registry()
    assert registry.provider_types() == ("aws", "azure", "bigquery", "databricks", "mariadb", "mysql", "oracle", "postgres", "presto", "snowflake", "sqlserver", "trino")
    provider = registry.create("trino")
    assert (
        provider.provider_version == "1"
        and Capability.QUERY_HISTORY in provider.capabilities().supported
        and Capability.LINEAGE_COLLECTION in provider.capabilities().unsupported
    )


def test_config_basic_jwt_certificate_and_bounds():
    assert parse_configuration(BASE).authentication.type == "basic"
    assert (
        parse_configuration(
            {**BASE, "authentication": {"type": "jwt", "user": "svc", "token_ref": "env:JWT"}}
        ).authentication.type
        == "jwt"
    )
    assert (
        parse_configuration(
            {
                **BASE,
                "authentication": {
                    "type": "certificate",
                    "user": "svc",
                    "certificate_ref": "file-ref:/cert",
                    "private_key_ref": "file-ref:/key",
                },
            }
        ).authentication.type
        == "certificate"
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"tls": {"verify": False}},
        {"host": "https://x"},
        {"headers": {"x": "y"}},
        {"authentication": {"type": "basic", "username": "u", "password": "inline"}},
        {"authentication": {"type": "jwt", "user": "u", "token": "inline"}},
        {"authentication": {"type": "oauth2", "user": "u"}},
        {"authentication": {"type": "kerberos", "user": "u"}},
    ],
)
def test_rejected_configuration(patch):
    with pytest.raises(ValueError):
        parse_configuration({**BASE, **patch})


def test_missing_dependency_is_safe(monkeypatch):
    import integrations.trino.connection as module

    monkeypatch.setattr(module.importlib, "import_module", lambda _: (_ for _ in ()).throw(ImportError()))
    context = IntegrationContext("tenant", "integration", "run", datetime.now(timezone.utc) + timedelta(seconds=10))
    result = asyncio.run(TrinoSqlEngineProvider().test_connection(context, BASE))
    assert not result.connected and str(result.error_code) == "dependency_unavailable"


def test_all_sql_is_metadata_only_and_private():
    statements = list(REGISTRY.all()) + list(catalog_registry("hive").all())
    for statement in statements:
        sql = statement.sql.lower()
        assert "select *" not in sql and "system.query(" not in sql and "kill_query" not in sql
        assert not any(
            word in sql.split() for word in ("insert", "update", "delete", "create", "alter", "drop", "call")
        )
        assert any(
            scope in sql
            for scope in ("information_schema", "system.metadata", "system.runtime", "select 1", "version()")
        )
    query = REGISTRY.get("queries").sql.lower().split(" from ")[0]
    assert " query," not in query and " user" not in query and " source" not in query
    assert "source <> 'dataobs-collector'" in REGISTRY.get("queries").sql
    tasks = REGISTRY.get("tasks").sql.lower().split(" from ")[0]
    assert "node_id" not in tasks and "task_id," not in tasks and "stage_id" not in tasks
