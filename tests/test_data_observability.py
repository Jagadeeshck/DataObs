from fastapi.testclient import TestClient

from src.api.app import StoreBundle, create_app
from src.api.store import InMemoryStore
from src.config.settings import APISettings, AppSettings, AuthSettings, ElasticsearchSettings, ObservabilitySettings, RuntimeSettings, TenantSettings
from src.data_observability.service import calculate_asset_health, parse_openlineage_event


def settings():
    return AppSettings(RuntimeSettings(env="test"), APISettings(), ElasticsearchSettings(), AuthSettings(allow_unauthenticated_dev=True), TenantSettings(), ObservabilitySettings(), store_backend="memory")


def client():
    return TestClient(create_app(settings=settings(), store_bundle=StoreBundle(store=InMemoryStore())))


def test_asset_health_states():
    assert calculate_asset_health({}, [], []) == "unknown"
    assert calculate_asset_health({}, [{"status":"pass", "severity":"critical"}], []) == "healthy"
    assert calculate_asset_health({}, [{"status":"failed", "severity":"warning"}], []) == "warning"
    assert calculate_asset_health({}, [{"status":"failed", "severity":"critical"}], []) == "critical"
    assert calculate_asset_health({}, [], [{"status":"failed"}]) == "critical"


def test_parse_openlineage_event():
    parsed = parse_openlineage_event({"eventType":"COMPLETE","eventTime":"2026-07-08T00:00:00Z","run":{"runId":"r1"},"job":{"name":"job"},"inputs":[{"namespace":"db","name":"in"}],"outputs":[{"namespace":"db","name":"out"}]})
    assert parsed["job_name"] == "job"
    assert parsed["run_id"] == "r1"
    assert parsed["status"] == "success"
    assert parsed["input_assets"] == ["db:in"]
    assert parsed["output_assets"] == ["db:out"]


def test_asset_creation_and_search_api():
    c = client()
    resp = c.post("/api/data-observability/assets", json={"asset_id":"a1","name":"Orders","asset_type":"table","source_system":"warehouse","owner":"data","domain":"commerce","criticality":"critical","tags":["orders"],"description":"Order table"})
    assert resp.status_code == 201
    assert resp.json()["asset_id"] == "a1"
    resp = c.get("/api/data-observability/assets", params={"q":"ord"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_quality_run_ingestion_and_health_api():
    c = client()
    c.post("/api/data-observability/assets", json={"asset_id":"a1","name":"Orders"})
    resp = c.post("/api/data-observability/quality-runs", json={"check_id":"c1","asset_id":"a1","status":"failed","observed_value":5,"expected_value":0,"severity":"critical","message":"bad","duration_ms":1})
    assert resp.status_code == 201
    assert c.get("/api/data-observability/quality-runs", params={"asset_id":"a1"}).json()["count"] == 1
    assert c.get("/api/data-observability/assets/a1/health").json()["health_status"] == "critical"


def test_lineage_openlineage_ingestion_and_lookup_api():
    c = client()
    resp = c.post("/api/data-observability/lineage/events", json={"eventType":"COMPLETE","eventTime":"2026-07-08T00:00:00Z","run":{"runId":"r1"},"job":{"name":"job"},"inputs":[{"namespace":"db","name":"in"}],"outputs":[{"namespace":"db","name":"out"}]})
    assert resp.status_code == 201
    assert len(resp.json()["lineage_edges"]) == 1
    lineage = c.get("/api/data-observability/assets/db:in/lineage").json()
    assert lineage["downstream"][0]["target_asset_id"] == "db:out"
