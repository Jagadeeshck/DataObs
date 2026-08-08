import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from integrations.databases.postgres.configuration import parse_configuration
from integrations.databases.postgres.provider import PostgreSqlDatabaseProvider
from packages.collectors.sdk import Capability, IntegrationContext
from services.collection_manager.cli import build_registry


def config(**updates):
    value = {
        "host": "db.internal",
        "database": "app",
        "authentication": {"type": "password", "username": "collector", "password_ref": "env:PASSWORD"},
        "tls": {"mode": "verify-full"},
    }
    value.update(updates)
    return value


def test_registration_version_capabilities_and_config_safety():
    provider = build_registry().create("postgres")
    assert provider.provider_version == "1"
    assert Capability.QUERY_HISTORY not in provider.capabilities().supported
    assert Capability.LINEAGE_COLLECTION not in provider.capabilities().supported
    assert parse_configuration(config()).tls_mode == "verify-full"
    for tls in ("disable", "allow", "prefer", "require"):
        with pytest.raises(ValueError):
            parse_configuration(config(tls={"mode": tls}))
    with pytest.raises(ValueError):
        parse_configuration(config(authentication={"type": "password", "username": "u", "password": "inline"}))
    with pytest.raises(ValueError):
        parse_configuration(config(unknown=True))


class Cursor:
    description = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, parameters=()):
        assert "SELECT *" not in sql.upper()

    def fetchmany(self, count):
        return []


class Connection:
    closed = False

    def cursor(self):
        return Cursor()

    def close(self):
        self.closed = True


class Factory:
    def __init__(self):
        self.connection = Connection()

    def connect(self, cfg):
        outer = self

        class Manager:
            def __enter__(self):
                return outer.connection

            def __exit__(self, *args):
                outer.connection.close()

        return Manager()


def test_independent_provider_closes_connection_and_emits_no_rows():
    factory = Factory()
    provider = PostgreSqlDatabaseProvider(factory)
    context = IntegrationContext(
        "tenant",
        "integration",
        "run",
        datetime.now(timezone.utc) + timedelta(seconds=30),
        attributes={"environment": "prod"},
    )
    assert asyncio.run(provider.validate_configuration(context, config())).valid
    request = type("Request", (), {"capabilities": frozenset({Capability.METADATA_COLLECTION})})()

    async def collect():
        return [x async for x in provider.collect(context, request)]

    assert asyncio.run(collect()) == []
    assert factory.connection.closed
