"""
Pytest fixtures for service-backed integration tests.

Requires Docker and an already-running integration stack. Run with:
    RUN_INTEGRATION_TESTS=1 pytest tests/integration/ -v --timeout=120

Resolves: https://github.com/Jagadeeshck/DataObs/issues/25
"""
from __future__ import annotations

import os
import time

import pytest

requests = pytest.importorskip("requests", reason="integration tests require the requests package")

API_BASE = "http://localhost:8000"
ES_BASE = "http://localhost:9200"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip service-backed tests unless the developer opts in explicitly."""

    if os.getenv("RUN_INTEGRATION_TESTS") == "1":
        return
    skip_integration = pytest.mark.skip(reason="set RUN_INTEGRATION_TESTS=1 to run service-backed integration tests")
    for item in items:
        if "tests/integration" in item.path.as_posix():
            item.add_marker(skip_integration)


def _wait_for(url: str, timeout: int = 60, interval: float = 2.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(interval)
    return False


@pytest.fixture(scope="session")
def api_client():
    """Wait for the DataObs API to be healthy, return base URL."""
    assert _wait_for(f"{API_BASE}/health"), "DataObs API did not become healthy"
    return API_BASE


@pytest.fixture(scope="session")
def es_client():
    """Wait for Elasticsearch to be healthy, return base URL."""
    assert _wait_for(f"{ES_BASE}/_cluster/health"), "Elasticsearch did not become healthy"
    return ES_BASE
