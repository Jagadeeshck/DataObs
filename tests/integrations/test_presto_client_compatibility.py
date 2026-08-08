"""Official-client gate. Full DBAPI lifecycle uses fakes by default; live mode is opt-in."""

import importlib
import os

import pytest


def test_official_client_import_and_basic_authentication():
    pytest.importorskip("prestodb")
    from prestodb.auth import BasicAuthentication

    assert BasicAuthentication("collector", "secret") is not None


@pytest.mark.skipif(os.getenv("RUN_PRESTO_INTEGRATION_TESTS") != "1", reason="requires disposable Presto")
def test_live_presto_dbapi_lifecycle():
    dbapi = importlib.import_module("prestodb.dbapi")
    connection = dbapi.connect(
        host=os.environ["PRESTO_HOST"],
        port=int(os.getenv("PRESTO_PORT", "8443")),
        protocol="https",
        user="dataobs_collector",
        source="dataobs-collector",
        requests_kwargs={"verify": True},
    )
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT 1 AS reachable")
        assert cursor.fetchmany(1) == [[1]]
    finally:
        cursor.close()
        connection.close()
