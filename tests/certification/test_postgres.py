"""Live PostgreSQL discovery and DataObs persistence certification."""

import os

import pytest

from tests.certification.clients.postgres import PostgresClient

pytestmark = pytest.mark.postgres


def test_postgres_provider_and_dataobs_storage_are_live(live_stack):
    api, es = live_stack
    with PostgresClient().connect() as connection:
        assert connection.info.transaction_status is not None
        with connection.cursor() as cursor:
            cursor.execute("select schema_name from information_schema.schemata")
            schemas = {row[0] for row in cursor.fetchall()}
    assert {"public", "analytics", "restricted"} <= schemas
    assert api.request("/health")["status"] in {"ok", "healthy"}
    assert es.request("/_cat/indices?format=json", expected=(200,)) is not None
    assert "DATAOBS_CERT_SENTINEL_DB_PASSWORD" not in str(es.request("/_search?size=0", expected=(200,))).upper()


def test_runtime_password_file_is_restrictive():
    if os.getenv("RUN_CERTIFICATION_TESTS") != "1":
        pytest.skip("hosted runtime secret only")
    path = os.environ["CERTIFICATION_POSTGRES_PASSWORD_FILE"]
    assert os.stat(path).st_mode & 0o077 == 0
    assert not path.endswith("postgres-password.example.txt")
