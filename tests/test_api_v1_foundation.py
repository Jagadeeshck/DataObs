from fastapi.testclient import TestClient

from src.api.app import create_app


def test_api_v1_scanner_asset_flow_and_health():
    c = TestClient(create_app())
    h = {"X-DataObs-Tenant": "t1"}
    assert c.get("/livez").json()["status"] == "ok"
    assert c.get("/health").headers["deprecation"] == "true"
    assert (
        c.post(
            "/api/v1/tenants", json={"tenant_id": "t1", "display_name": "Tenant 1", "namespace": "t1"}, headers=h
        ).status_code
        == 201
    )
    src = c.post(
        "/api/v1/sources",
        json={
            "source_name": "pg",
            "source_type": "postgres",
            "connector_type": "postgres",
            "endpoint": {"host": "db"},
            "credential_ref": "vault://pg",
        },
        headers=h,
    ).json()
    scanner = c.post("/api/v1/scanners", json={"scanner_identity": "s1", "version": "0.1"}, headers=h).json()
    assert (
        c.post(f"/api/v1/scanners/{scanner['id']}/heartbeat", json={"health": "healthy"}, headers=h).status_code == 200
    )
    c.post(
        "/api/v1/scan-policies",
        json={"source_id": src["id"], "connector": "postgres", "operation": "schema_snapshot", "enabled": True},
        headers=h,
    )
    task = c.get(f"/api/v1/scanners/{scanner['id']}/tasks", headers=h).json()["items"][0]
    c.post(f"/api/v1/scanners/{scanner['id']}/tasks/{task['id']}/ack", json={}, headers=h)
    result = c.post(
        f"/api/v1/scanners/{scanner['id']}/tasks/{task['id']}/results",
        json={
            "source_id": src["id"],
            "fully_qualified_name": "db.public.orders",
            "namespace": "db",
            "asset_type": "table",
            "schema": {"columns": []},
        },
        headers={**h, "Idempotency-Key": "k"},
    ).json()
    assert c.get("/api/v1/assets", headers=h).json()["items"][0]["id"] == result["asset_id"]
    assert c.get(f"/api/v1/assets/{result['asset_id']}", headers={"X-DataObs-Tenant": "other"}).status_code == 404
    assert {p["pillar"] for p in c.get("/api/v1/pillars", headers=h).json()["pillars"]} >= {
        "platform",
        "data_pipeline",
        "data",
        "finops_cost",
        "business",
        "ai_agent",
    }
