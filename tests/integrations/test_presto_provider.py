import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from integrations.presto import PrestoSqlEngineProvider
from integrations.presto.configuration import parse_configuration
from integrations.presto.connection import validate_next_uri
from integrations.presto.dialect import PrestoDialect
from integrations.presto.normalisation import connector_category, resource
from integrations.presto.sql import REGISTRY, catalog_registry
from integrations.sql_engine import FixedStatement, FixedStatementRegistry
from packages.collectors.sdk import Capability, IntegrationContext
from services.collection_manager.cli import build_registry

BASE = {
    "host": "presto.example.internal",
    "port": 8443,
    "authentication": {"type": "basic", "username": "dataobs_collector", "password_ref": "env:SECRET"},
    "tls": {"verify": True},
}


def test_registry_identity_capabilities():
    p = build_registry().create("presto")
    assert p.provider_type == "presto" and p.provider_version == "1"
    assert Capability.QUERY_HISTORY in p.capabilities().supported
    assert Capability.LINEAGE_COLLECTION in p.capabilities().unsupported


def test_basic_configuration_is_closed():
    assert parse_configuration(BASE).authentication.type == "basic"


@pytest.mark.parametrize(
    "patch",
    [
        {"tls": {"verify": False}},
        {"host": "https://x"},
        {"host": "127.0.0.1"},
        {"headers": {}},
        {"authentication": {"type": "basic", "username": "u", "password": "inline"}},
        {"authentication": {"type": "jwt", "username": "u", "password_ref": "env:X"}},
        {"session_properties": {}},
    ],
)
def test_dangerous_configuration_rejected(patch):
    with pytest.raises(ValueError):
        parse_configuration({**BASE, **patch})


def test_missing_dependency_is_safe(monkeypatch):
    import integrations.presto.connection as module

    monkeypatch.setattr(module.importlib, "import_module", lambda _: (_ for _ in ()).throw(ImportError()))
    c = IntegrationContext("tenant", "integration", "run", datetime.now(timezone.utc) + timedelta(seconds=10))
    result = asyncio.run(PrestoSqlEngineProvider().test_connection(c, BASE))
    assert not result.connected and result.error_code == "dependency_unavailable"


def test_sql_is_registered_metadata_only_private():
    statements = REGISTRY.all() + catalog_registry("hive").all()
    for statement in statements:
        sql = statement.sql.lower()
        assert "select *" not in sql and "kill_query" not in sql
        assert any(
            x in sql for x in ("information_schema", "system.metadata", "system.runtime", "select 1", "version()")
        )
        assert not any(
            x in sql.split() for x in ("insert", "update", "delete", "merge", "create", "alter", "drop", "call")
        )
    projection = REGISTRY.get("queries").sql.lower().split(" from ")[0]
    assert " query," not in projection and " user" not in projection and " source" not in projection
    assert "source <> 'dataobs-collector'" in REGISTRY.get("queries").sql
    task_projection = REGISTRY.get("tasks").sql.lower().split(" from ")[0]
    assert "node_id" not in task_projection and "task_id," not in task_projection and "stage_id" not in task_projection


def test_mutations_and_session_are_rejected():
    for sql in (
        "CALL system.runtime.kill_query('x')",
        "SET SESSION x = 'y'",
        "START TRANSACTION",
        "COMMIT",
        "EXECUTE IMMEDIATE 'x'",
    ):
        with pytest.raises(ValueError):
            FixedStatementRegistry((FixedStatement("bad", sql, "bad"),))


def test_materialized_views_explicitly_unsupported():
    assert PrestoDialect.materialized_view_inventory == "unsupported" and all(
        "materialized" not in x.sql for x in REGISTRY.all()
    )


@pytest.mark.parametrize(
    "uri",
    [
        "http://presto.example.internal:8443/v1/x",
        "https://evil.example:8443/v1/x",
        "https://u:p@presto.example.internal:8443/v1/x",
        "https://presto.example.internal:8444/v1/x",
    ],
)
def test_unsafe_next_uri_rejected(uri):
    with pytest.raises(RuntimeError):
        validate_next_uri(uri, "presto.example.internal", 8443)


def test_safe_next_uri():
    validate_next_uri("https://presto.example.internal:8443/v1/statement/x/1", "presto.example.internal", 8443)


def test_connector_categories_are_conservative():
    assert connector_category("hive") == "hive/lakehouse" and connector_category("custom") == "unknown"


def test_redaction_and_bounded_history():
    c = IntegrationContext("tenant", "integration", "run", datetime.now(timezone.utc) + timedelta(seconds=10))
    item = resource(
        c, "cluster", "runtime_queries", "q", {"query_id": "q", "query": "secret", "user": "alice", "source": "x"}
    )
    assert (
        "query" not in item.source_evidence
        and "user" not in item.source_evidence
        and item.source_evidence["history_completeness"] == "bounded_runtime_history"
    )
