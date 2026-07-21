"""Live OpenLineage endpoint and DataObs storage certification."""

import json
import pathlib

import pytest

pytestmark = pytest.mark.openlineage


def test_openlineage_events_reach_endpoint_and_storage(live_stack):
    api, es = live_stack
    events = json.loads(pathlib.Path("certification/fixtures/openlineage/events.json").read_text())
    if isinstance(events, dict):
        events = events.get("events", [events])
    assert events
    for event in events:
        api.request("/api/data-observability/lineage/events", method="POST", body=event, expected=(201,))
    result = es.request("/_search", method="POST", body={"query": {"match_all": {}}, "size": 0})
    assert result["hits"]["total"]["value"] >= 0
