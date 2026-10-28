from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.security.models import Principal, TenantAccess
from src.security.permissions import Permission


def test_api_v1_scanner_asset_flow_and_health():
    app = create_app()
    # This is a scanner/asset contract test, not a platform administrator journey.
    # Model an already authenticated, narrowly authorized collection manager.
    app.state.authenticator = Mock()
    app.state.authenticator.authenticate.return_value = Principal(
        subject="scanner-test",
        issuer="https://identity.example.test",
        principal_type="service",
        permissions=frozenset(
            {
                Permission.COLLECTION_MANAGE,
                Permission.INTEGRATIONS_WRITE,
                Permission.ASSETS_READ,
            }
        ),
        tenant_access=frozenset({TenantAccess("t1", frozenset({"test"}))}),
    )
    c = TestClient(app)
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
    denied = c.get(f"/api/v1/assets/{result['asset_id']}", headers={"X-DataObs-Tenant": "other"})
    assert denied.status_code == 403
    assert "tenant_access_denied" in denied.text
    # A collection identity cannot administer IAM, even within its own tenant.
    assert c.post("/api/v1/iam/role-bindings", json={}, headers=h).status_code == 403
    assert {p["pillar"] for p in c.get("/api/v1/pillars", headers=h).json()["pillars"]} >= {
        "platform",
        "data_pipeline",
        "data",
        "finops_cost",
        "business",
        "ai_agent",
    }
