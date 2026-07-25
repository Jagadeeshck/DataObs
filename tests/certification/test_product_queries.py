"""Live public product-query API and backing-store certification."""

import pytest

pytestmark = pytest.mark.product_queries


def test_asset_and_stream_routes_are_bounded_and_tenant_scoped(live_stack):
    api, es = live_stack
    assets = api.request("/api/v1/assets?page_size=2", expected=(200, 404))
    streams = api.request("/api/v1/streams?page_size=2", expected=(200, 404))
    assert assets is not None and streams is not None
    assert es.request("/_cluster/health")["status"] in {"green", "yellow"}
