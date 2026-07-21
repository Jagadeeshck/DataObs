import os

import pytest

from tests.certification.clients.api import ApiClient
from tests.certification.clients.elasticsearch import ElasticsearchClient


def pytest_configure(config):
    for marker in (
        "migrations",
        "postgres",
        "kafka",
        "openlineage",
        "product_queries",
        "incidents",
        "otel",
        "security",
        "browser",
    ):
        config.addinivalue_line("markers", f"{marker}: certification capability evidence group")


def require_live_certification():
    """Skip locally, but fail closed when hosted certification was requested."""
    if os.getenv("RUN_CERTIFICATION_TESTS") != "1":
        pytest.skip("requires RUN_CERTIFICATION_TESTS=1 and the bounded live stack")
    ApiClient().wait("/health", lambda value: isinstance(value, dict), deadline_seconds=30)
    ElasticsearchClient().wait(
        "/_cluster/health", lambda value: value.get("status") in {"green", "yellow"}, deadline_seconds=30
    )


@pytest.fixture
def live_stack():
    require_live_certification()
    return ApiClient(), ElasticsearchClient()
