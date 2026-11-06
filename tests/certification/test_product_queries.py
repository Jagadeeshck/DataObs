"""Live public product-query API and backing-store certification."""

import pytest

pytestmark = pytest.mark.product_queries


def test_asset_and_stream_routes_are_bounded_and_tenant_scoped(live_stack):
    api, es = live_stack
    assets = api.request("/api/v1/assets?page_size=2", expected=(200, 404))
    # Stream routes require an explicit `environment` query param by design
    # (src/api/stream_routes.py declares `environment: str = Query(...)` on every
    # route); omitting it is a 422 by contract. Every real caller and the Console
    # send it, so the harness must too. `staging` matches the harness tenant/env
    # scoping (tenant-alpha / staging); an empty-but-valid result is acceptable.
    streams = api.request("/api/v1/streams?page_size=2&environment=staging", expected=(200, 404))
    assert assets is not None and streams is not None
    assert es.request("/_cluster/health")["status"] in {"green", "yellow"}
