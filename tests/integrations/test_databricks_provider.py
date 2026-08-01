from datetime import datetime, timedelta, timezone

import pytest

from integrations.databricks.configuration import parse_configuration, validate_workspace_host
from integrations.databricks.normalisation import SAFE_FIELDS, allowlist
from integrations.databricks.pagination import Page, collect_pages
from integrations.databricks.provider import DatabricksLakehouseProvider
from integrations.databricks.system_tables import QUERY_HISTORY_SQL, WAREHOUSE_EVENTS_SQL, validate_templates
from packages.collectors.sdk import Capability, ProviderRegistry


def config(auth=None):
    return {
        "cloud": "aws",
        "workspace_host": "https://dbc-00000000-0000.cloud.databricks.com/",
        "expected_workspace_id": "123456789",
        "authentication": auth
        or {"type": "oauth_m2m", "client_id_ref": "env:CLIENT", "client_secret_ref": "env:SECRET"},
        "system_tables": {"enabled": False},
    }


def test_registration_capabilities_and_version():
    registry = ProviderRegistry()
    registry.register(DatabricksLakehouseProvider)
    assert registry.provider_types() == ("databricks",)
    assert DatabricksLakehouseProvider.provider_version == "1"
    provider = registry.create("databricks")
    assert Capability.QUERY_HISTORY in provider.capabilities().supported
    assert Capability.LINEAGE_COLLECTION in provider.capabilities().unsupported
    with pytest.raises(ValueError):
        registry.register(DatabricksLakehouseProvider)


@pytest.mark.parametrize(
    "host",
    [
        "http://dbc-x.cloud.databricks.com",
        "https://127.0.0.1",
        "https://accounts.cloud.databricks.com",
        "https://evil.example",
        "https://dbc-x.cloud.databricks.com/path",
        "https://u:p@dbc-x.cloud.databricks.com",
    ],
)
def test_unsafe_hosts_rejected(host):
    with pytest.raises(Exception):
        validate_workspace_host(host, "aws")


def test_configuration_is_closed_and_credentials_are_references():
    assert parse_configuration(config()).workspace_host == "https://dbc-00000000-0000.cloud.databricks.com"
    with pytest.raises(Exception):
        parse_configuration({**config(), "api_path": "/api/2.0"})
    with pytest.raises(Exception):
        parse_configuration(config({"type": "oauth_m2m", "client_id_ref": "inline", "client_secret_ref": "env:S"}))
    with pytest.raises(Exception):
        parse_configuration(config({"type": "pat_legacy", "token_ref": "env:T"}))
    assert (
        parse_configuration(
            {**config({"type": "pat_legacy", "token_ref": "env:T"}), "allow_legacy_pat": True}
        ).authentication.type
        == "pat_legacy"
    )


def test_pagination_empty_page_dedup_order_and_token_loop():
    pages = {None: Page(({"id": "b"},), "a"), "a": Page((), "b"), "b": Page(({"id": "a"}, {"id": "b"}))}
    assert [
        x["id"] for x in collect_pages(lambda t: pages[t], key=lambda x: x["id"], maximum_pages=4, maximum_results=3)
    ] == ["a", "b"]
    with pytest.raises(Exception, match="Databricks collection failed"):
        collect_pages(lambda _: Page((), "same"), key=str, maximum_pages=3, maximum_results=3)
    with pytest.raises(Exception):
        collect_pages(lambda _: Page((), "x"), key=str, maximum_pages=3, maximum_results=3, cancelled=lambda: True)


def test_allowlists_remove_sensitive_provider_fields():
    raw = {
        "id": "w",
        "name": "safe",
        "hostname": "sensitive",
        "http_path": "sensitive",
        "odbc_params": {"token": "x"},
        "owner": "user",
        "storage_location": "s3://secret",
    }
    assert allowlist(raw, SAFE_FIELDS["warehouse"]) == {"id": "w", "name": "safe"}
    assert allowlist(raw, SAFE_FIELDS["volume"]) == {"name": "safe"}


def test_fixed_sql_is_bounded_workspace_filtered_and_private():
    validate_templates()
    for sql in (QUERY_HISTORY_SQL, WAREHOUSE_EVENTS_SQL):
        upper = sql.upper()
        assert "SELECT *" not in upper and "STATEMENT_TEXT" not in upper and "ERROR_MESSAGE" not in upper
        assert "WORKSPACE_ID = :WORKSPACE_ID" in upper and "ORDER BY" in upper and "LIMIT :ROW_LIMIT" in upper


@pytest.mark.skipif(
    __import__("os").environ.get("RUN_DATABRICKS_INTEGRATION_TESTS") != "1",
    reason="requires RUN_DATABRICKS_INTEGRATION_TESTS=1 and approved synthetic workspace",
)
def test_live_databricks_read_only_boundary():
    pytest.skip("live OAuth secret references and approved synthetic workspace are unavailable")
