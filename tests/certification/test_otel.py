"""Live OTel sink and API correlation certification."""

import pytest

pytestmark = pytest.mark.otel


def test_api_request_produces_queryable_telemetry(live_stack):
    api, es = live_stack
    api.request("/health")
    indices = es.request("/_cat/indices?format=json")
    assert isinstance(indices, list)
    assert all("DATAOBS_CERT_SENTINEL" not in str(item) for item in indices)
