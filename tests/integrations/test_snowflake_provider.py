from datetime import datetime, timedelta, timezone

import pytest

from integrations.snowflake.configuration import parse_configuration
from integrations.snowflake.credentials import CredentialResolver
from integrations.snowflake.provider import SnowflakeWarehouseProvider
from integrations.snowflake.sql import SQL_TEMPLATES, execute_bounded
from packages.collectors.sdk import Capability, ProviderRegistry


def config(auth=None):
    return {
        "account_identifier": "synthetic-org.synthetic-account",
        "user": "COLLECTOR",
        "role": "MONITOR",
        "authentication": auth or {"type": "key_pair", "private_key_ref": "env:KEY"},
        "include_databases": ["ANALYTICS"],
        "exclude_schemas": ["INFORMATION_SCHEMA"],
    }


def test_registration_and_capabilities():
    registry = ProviderRegistry()
    registry.register(SnowflakeWarehouseProvider)
    assert registry.provider_types() == ("snowflake",)
    assert SnowflakeWarehouseProvider.provider_version == "1"
    assert Capability.QUERY_HISTORY in registry.create("snowflake").capabilities().supported
    with pytest.raises(ValueError):
        registry.register(SnowflakeWarehouseProvider)


@pytest.mark.parametrize(
    "auth",
    [
        {"type": "password", "password": "bad"},
        {"type": "externalbrowser"},
        {"type": "oauth", "oauth_token_ref": "raw-token"},
    ],
)
def test_unsafe_authentication_is_rejected(auth):
    with pytest.raises(Exception):
        parse_configuration(config(auth))


def test_supported_authentication_references(monkeypatch):
    monkeypatch.setenv("KEY", "secret")
    assert CredentialResolver().resolve("env:KEY") == "secret"
    assert parse_configuration(config({"type": "oauth", "oauth_token_ref": "env:TOKEN"})).authentication.type == "oauth"
    assert (
        parse_configuration(
            config({"type": "workload_identity", "identity_provider": "AWS"})
        ).authentication.identity_provider
        == "AWS"
    )


def test_all_templates_are_safe_and_bounded():
    for template in SQL_TEMPLATES.values():
        text = " ".join(template.text.upper().split())
        assert "SELECT *" not in text
        assert "QUERY_TEXT" not in text
        assert " ORDER BY " in text or template.family == "account"
        assert " LIMIT %(LIMIT)S" in text
        if template.historical:
            assert "%(START_TIME)S" in text


class Cursor:
    description = (("VALUE",),)

    def __init__(self):
        self.closed = False
        self.calls = 0

    def execute(self, sql, params):
        assert params["limit"] == 1

    def fetchmany(self, size):
        self.calls += 1
        return [(0,)] if self.calls == 1 else []

    def close(self):
        self.closed = True


def test_bounded_fetch_preserves_zero_and_closes_cursor():
    cursor = Cursor()
    connection = type("Connection", (), {"cursor": lambda self: cursor})()
    assert list(execute_bounded(connection, SQL_TEMPLATES["account"], {"limit": 1}, batch_size=1)) == [{"value": 0}]
    assert cursor.closed and cursor.calls == 2


def test_configuration_is_closed_and_bounded():
    with pytest.raises(Exception):
        parse_configuration({**config(), "host": "attacker.invalid"})
    with pytest.raises(Exception):
        parse_configuration({**config(), "history": {"query_lookback_seconds": 9999999}})
