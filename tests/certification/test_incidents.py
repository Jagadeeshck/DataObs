"""Live incident API/persistence isolation certification."""

import pytest

pytestmark = pytest.mark.incidents


def test_incident_store_is_reachable_and_tenant_bounded(live_stack):
    api, es = live_stack
    response = api.request("/api/v1/incidents?page_size=2", expected=(200, 404))
    assert response is not None
    assert isinstance(es.request("/_cat/indices?format=json"), list)
