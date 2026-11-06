"""
Pytest fixtures for service-backed integration tests.

Requires Docker and an already-running integration stack. Run with:
    RUN_INTEGRATION_TESTS=1 pytest tests/integration/ -v --timeout=120

Resolves: https://github.com/Jagadeeshck/DataObs/issues/25
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

requests = pytest.importorskip("requests", reason="integration tests require the requests package")

API_BASE = "http://localhost:8000"
ES_BASE = "http://localhost:9200"
OTEL_COLLECTOR_HEALTH = "http://localhost:13133"

# ---------------------------------------------------------------------------
# Index template for dataobs-traces
# ES 9.x strict dynamic mapping would reject OTel span documents that contain
# nested dot-notation attribute keys (e.g. attributes.dataobs.table) unless an
# explicit template with dynamic: true and keyword mappings is in place.
# ---------------------------------------------------------------------------
_TRACES_INDEX_TEMPLATE = {
    "index_patterns": ["dataobs-traces*"],
    "template": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "dynamic": True,
            "properties": {
                "@timestamp": {"type": "date"},
                "trace_id": {"type": "keyword"},
                "span_id": {"type": "keyword"},
                "parent_span_id": {"type": "keyword"},
                "name": {"type": "keyword"},
                "kind": {"type": "integer"},
                "start_time_unix_nano": {"type": "long"},
                "end_time_unix_nano": {"type": "long"},
                "duration_nano": {"type": "long"},
                "status": {
                    "type": "object",
                    "dynamic": True,
                },
                "attributes": {
                    "type": "object",
                    "dynamic": True,
                },
                "resource": {
                    "type": "object",
                    "dynamic": True,
                },
                "scope": {
                    "type": "object",
                    "dynamic": True,
                },
                "events": {
                    "type": "nested",
                    "dynamic": True,
                },
            },
        },
    },
    "priority": 200,
    "composed_of": [],
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip service-backed tests unless the developer opts in explicitly."""

    if os.getenv("RUN_INTEGRATION_TESTS") == "1":
        return
    skip_integration = pytest.mark.skip(reason="set RUN_INTEGRATION_TESTS=1 to run service-backed integration tests")
    for item in items:
        if Path(__file__).resolve().parent in item.path.resolve().parents:
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


def _ensure_traces_index_template(es_base: str) -> None:
    """Create or update the dataobs-traces index template in ES.

    This is idempotent — PUT with the same body is a no-op after first run.
    The template ensures ES 9.x accepts OTel-formatted span documents without
    rejecting dynamic dot-notation attribute fields.
    """
    url = f"{es_base}/_index_template/dataobs-traces-template"
    resp = requests.put(url, json=_TRACES_INDEX_TEMPLATE, timeout=10)
    assert resp.status_code in (200, 201), (
        f"Failed to create dataobs-traces index template: {resp.status_code} {resp.text}"
    )


@pytest.fixture(scope="session")
def api_client():
    """Wait for the DataObs API to be healthy, return base URL."""
    assert _wait_for(f"{API_BASE}/health"), "DataObs API did not become healthy"
    return API_BASE


@pytest.fixture(scope="session")
def es_client():
    """Wait for Elasticsearch to be healthy, create required index templates, return base URL."""
    assert _wait_for(f"{ES_BASE}/_cluster/health"), "Elasticsearch did not become healthy"
    # Ensure the dataobs-traces template exists before any OTel spans arrive.
    # Without it, ES 9.5.5 may reject documents with nested attribute keys.
    _ensure_traces_index_template(ES_BASE)
    return ES_BASE


@pytest.fixture(scope="session")
def otel_collector():
    """Wait for the OTel Collector health endpoint to be ready."""
    assert _wait_for(OTEL_COLLECTOR_HEALTH, timeout=60), "OTel Collector did not become healthy"
    return OTEL_COLLECTOR_HEALTH
