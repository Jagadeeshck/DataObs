from services.product_query.filters import isolation_filters


def test_shared_projection_filters_tenant_environment_and_source():
    assert isolation_filters("tenant-a", "prod", "otel-a") == [
        {"term": {"tenant_id": "tenant-a"}},
        {"term": {"environment": "prod"}},
        {"term": {"integration_id": "otel-a"}},
    ]
