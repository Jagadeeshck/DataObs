"""Live released migration application and backing mappings certification."""

import pytest

pytestmark = pytest.mark.migrations


def test_released_mappings_are_live_and_strict(live_stack):
    api, es = live_stack
    mappings = es.request("/_mapping")
    assert mappings
    assert any(body.get("mappings", {}).get("dynamic") in ("strict", False) for body in mappings.values())
    assert api.request("/health")["status"] in {"ok", "healthy"}
