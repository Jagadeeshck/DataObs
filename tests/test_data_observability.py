from fastapi.testclient import TestClient

from src.api.app import StoreBundle, create_app
from src.api.store import InMemoryStore
from src.config.settings import (
    APISettings,
    AppSettings,
    AuthSettings,
    ElasticsearchSettings,
    ObservabilitySettings,
    RuntimeSettings,
    TenantSettings,
)
from src.data_observability.openlineage import OpenLineageValidationError
from src.data_observability.service import calculate_asset_health, parse_openlineage_event


def settings():
    return AppSettings(
        RuntimeSettings(env="test"),
        APISettings(),
        ElasticsearchSettings(),
        AuthSettings(allow_unauthenticated_dev=True),
        TenantSettings(),
        ObservabilitySettings(),
        store_backend="memory",
    )


def client():
    return TestClient(create_app(settings=settings(), store_bundle=StoreBundle(store=InMemoryStore())))


def event(event_type="COMPLETE", event_time="2026-07-08T00:05:00Z"):
    return {
        "eventType": event_type,
        "eventTime": event_time,
        "producer": "https://dataobs.example/openlineage/test",
        "run": {"runId": "r1", "facets": {"nominalTime": {"nominalStartTime": "2026-07-08T00:00:00Z"}}},
        "job": {"namespace": "dbt", "name": "build_orders"},
        "inputs": [
            {
                "namespace": "warehouse",
                "name": "raw.orders",
                "facets": {
                    "schema": {"fields": [{"name": "order_id", "type": "string"}, {"name": "amount", "type": "double"}]}
                },
            }
        ],
        "outputs": [
            {
                "namespace": "warehouse",
                "name": "analytics.orders",
                "facets": {
                    "schema": {
                        "fields": [{"name": "order_id", "type": "string"}, {"name": "amount", "type": "double"}]
                    },
                    "columnLineage": {
                        "fields": {
                            "amount": {
                                "inputFields": [
                                    {
                                        "namespace": "warehouse",
                                        "name": "raw.orders",
                                        "field": "amount",
                                        "transformations": [
                                            {"type": "DIRECT", "subtype": "IDENTITY", "masking": False}
                                        ],
                                    }
                                ]
                            }
                        }
                    },
                    "dataQualityAssertions": {
                        "assertions": [
                            {
                                "assertion": "not_null",
                                "name": "orders_amount_not_null",
                                "column": "amount",
                                "success": True,
                                "severity": "error",
                            }
                        ]
                    },
                    "dataQualityMetrics": {"rowCount": 1200, "bytes": 24000},
                },
            }
        ],
    }


def test_asset_health_states():
    assert calculate_asset_health({}, [], []) == "unknown"
    assert calculate_asset_health({}, [{"status": "pass", "severity": "critical"}], []) == "healthy"
    assert calculate_asset_health({}, [{"status": "failed", "severity": "warning"}], []) == "warning"
    assert calculate_asset_health({}, [{"status": "failed", "severity": "critical"}], []) == "critical"
    assert calculate_asset_health({}, [], [{"status": "failed"}]) == "critical"


def test_parse_openlineage_event():
    parsed = parse_openlineage_event(event())
    assert parsed["job_name"] == "build_orders"
    assert parsed["job_namespace"] == "dbt"
    assert parsed["run_id"] == "r1"
    assert parsed["status"] == "success"
    assert parsed["input_assets"] == ["warehouse:raw.orders"]
    assert parsed["output_assets"] == ["warehouse:analytics.orders"]
    assert parsed["event_id"].startswith("ol_evt_")


def test_parse_openlineage_event_rejects_missing_job_namespace():
    payload = event()
    payload["job"].pop("namespace")
    try:
        parse_openlineage_event(payload)
        assert False, "expected OpenLineageValidationError"
    except OpenLineageValidationError as exc:
        assert "job.namespace" in str(exc)


def test_asset_creation_and_search_api():
    c = client()
    resp = c.post(
        "/api/data-observability/assets",
        json={
            "asset_id": "a1",
            "name": "Orders",
            "asset_type": "table",
            "source_system": "warehouse",
            "owner": "data",
            "domain": "commerce",
            "criticality": "critical",
            "tags": ["orders"],
            "description": "Order table",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["asset_id"] == "a1"
    resp = c.get("/api/data-observability/assets", params={"q": "ord"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_quality_run_ingestion_and_health_api():
    c = client()
    c.post("/api/data-observability/assets", json={"asset_id": "a1", "name": "Orders"})
    resp = c.post(
        "/api/data-observability/quality-runs",
        json={
            "check_id": "c1",
            "asset_id": "a1",
            "status": "failed",
            "observed_value": 5,
            "expected_value": 0,
            "severity": "critical",
            "message": "bad",
            "duration_ms": 1,
        },
    )
    assert resp.status_code == 201
    assert c.get("/api/data-observability/quality-runs", params={"asset_id": "a1"}).json()["count"] == 1
    assert c.get("/api/data-observability/assets/a1/health").json()["health_status"] == "critical"


def test_official_openlineage_endpoint_projects_facets_and_is_idempotent():
    c = client()
    response = c.post("/api/v1/lineage", json=event())
    assert response.status_code == 201
    body = response.json()
    assert body["deduplicated"] is False
    assert len(body["lineage_edges"]) == 1
    assert len(body["column_lineage_edges"]) == 1
    assert len(body["quality_runs"]) == 1
    assert len(body["columns"]) == 4

    duplicate = c.post("/api/v1/lineage", json=event())
    assert duplicate.status_code == 201
    assert duplicate.json()["deduplicated"] is True

    dataset = c.get("/api/v1/datasets/warehouse/analytics.orders").json()
    assert dataset["row_count"] == 1200
    column = c.get("/api/v1/lineage/warehouse:analytics.orders/columns/amount/upstream").json()
    assert column["count"] == 1


def test_openlineage_run_lifecycle_and_graph_traversal():
    c = client()
    start = event("START", "2026-07-08T00:00:00Z")
    complete = event("COMPLETE", "2026-07-08T00:05:00Z")
    assert c.post("/api/v1/lineage", json=start).status_code == 201
    assert c.post("/api/v1/lineage", json=complete).status_code == 201

    run = c.get("/api/v1/runs/r1")
    assert run.status_code == 200
    assert run.json()["status"] == "success"
    assert run.json()["duration_ms"] == 300000
    assert run.json()["event_count"] == 2

    job = c.get("/api/v1/jobs/dbt/build_orders")
    assert job.status_code == 200
    assert job.json()["qualified_name"] == "dbt:build_orders"

    lineage = c.get("/api/v1/lineage/warehouse:raw.orders/downstream", params={"depth": 3}).json()
    assert lineage["nodes"] == ["warehouse:analytics.orders"]


def test_legacy_lineage_ingestion_alias_remains_supported():
    c = client()
    resp = c.post("/api/data-observability/lineage/events", json=event())
    assert resp.status_code == 201
    lineage = c.get("/api/data-observability/assets/warehouse:raw.orders/lineage").json()
    assert lineage["downstream"][0]["target_asset_id"] == "warehouse:analytics.orders"


def test_invalid_openlineage_event_returns_structured_bad_request():
    c = client()
    response = c.post("/api/v1/lineage", json={"eventType": "COMPLETE"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"
