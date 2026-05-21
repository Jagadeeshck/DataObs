"""Endpoint compatibility tests for the FastAPI DataObs API."""
from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from src.api.app import StoreBundle, create_app
from src.config.settings import APISettings, AppSettings, AuthSettings, ElasticsearchSettings, ObservabilitySettings, RuntimeSettings, TenantSettings


class _FakeRuleStore:
    def __init__(self) -> None:
        self.rules: Dict[str, Dict[str, Any]] = {}

    def get_all_rules(self) -> List[Dict[str, Any]]:
        return list(self.rules.values())

    def add_rule(self, rule: Dict[str, Any]) -> str:
        rule_id = rule.get("rule_id", "rule-1")
        self.rules[rule_id] = {**rule, "rule_id": rule_id}
        return rule_id

    def delete_rule(self, rule_id: str) -> bool:
        return self.rules.pop(rule_id, None) is not None


class _FakeActiveStore(_FakeRuleStore):
    def __init__(self) -> None:
        super().__init__()
        self.results: Dict[str, Dict[str, Any]] = {}

    def save_quality_result(self, result: Dict[str, Any]) -> str:
        doc_id = result.get("id", "result-1")
        self.results[doc_id] = {**result, "id": doc_id}
        return doc_id

    def list_quality_results(self) -> List[Dict[str, Any]]:
        return list(self.results.values())

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        return [{"node_id": "rds.prod.orders", "type": "table"}]

    def get_all_edges(self) -> List[Dict[str, Any]]:
        return [{"source_node_id": "rds.prod.orders", "target_node_id": "rds.prod.reports"}]

    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]:
        return ["rds.prod.reports"] if node_id == "rds.prod.orders" else []


@pytest.fixture()
def client() -> TestClient:
    store = _FakeActiveStore()
    app = create_app(
        settings=AppSettings(runtime=RuntimeSettings(env="test"), api=APISettings(), elasticsearch=ElasticsearchSettings(), auth=AuthSettings(api_token=None), tenant=TenantSettings(), observability=ObservabilitySettings(), store_backend="memory"),
        store_bundle=StoreBundle(store=store),
    )
    return TestClient(app)


@pytest.fixture()
def client_with_auth() -> TestClient:
    store = _FakeActiveStore()
    app = create_app(
        settings=AppSettings(runtime=RuntimeSettings(env="test"), api=APISettings(), elasticsearch=ElasticsearchSettings(), auth=AuthSettings(api_token="test-secret-token", allow_unauthenticated_dev=False), tenant=TenantSettings(), observability=ObservabilitySettings(), store_backend="memory"),
        store_bundle=StoreBundle(store=store),
    )
    return TestClient(app)


def _auth(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Health check (no auth)
# ---------------------------------------------------------------------------

def test_health_check_returns_200(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "dataobs-api"


def test_health_check_no_auth_required(client_with_auth: TestClient):
    """Health endpoint must be reachable without a token (for load balancers)."""
    response = client_with_auth.get("/health")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Rules endpoint
# ---------------------------------------------------------------------------

def test_get_rules_returns_empty_list(client: TestClient):
    response = client.get("/rules")
    assert response.status_code == 200
    body = response.json()
    assert body["rules"] == []
    assert body["count"] == 0


def test_post_rule_creates_and_returns_id(client: TestClient):
    rule = {"dataset": "prod.orders", "check_type": "null_check", "severity": "critical"}
    response = client.post("/rules", json=rule)
    assert response.status_code == 201
    body = response.json()
    assert "rule_id" in body
    assert body["status"] == "created"


def test_post_rule_then_get_returns_it(client: TestClient):
    rule = {"dataset": "prod.orders", "check_type": "row_count", "severity": "high"}
    client.post("/rules", json=rule)

    response = client.get("/rules")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["rules"][0]["dataset"] == "prod.orders"


def test_delete_rule_preserves_response_shape(client: TestClient):
    created = client.post("/rules", json={"rule_id": "r-1", "dataset": "prod.orders"})
    assert created.status_code == 201

    response = client.delete("/rules/r-1")
    assert response.status_code == 200
    assert response.json() == {"rule_id": "r-1", "status": "deleted"}


# ---------------------------------------------------------------------------
# Lineage endpoints
# ---------------------------------------------------------------------------

def test_get_lineage_nodes(client: TestClient):
    response = client.get("/lineage/nodes")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["nodes"][0]["node_id"] == "rds.prod.orders"


def test_get_lineage_edges(client: TestClient):
    response = client.get("/lineage/edges")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1


def test_lineage_impact_returns_affected_nodes(client: TestClient):
    response = client.get("/lineage/impact/rds.prod.orders")
    assert response.status_code == 200
    body = response.json()
    assert body["root_node"] == "rds.prod.orders"
    assert "rds.prod.reports" in body["affected"]


def test_lineage_impact_unknown_node_returns_empty(client: TestClient):
    response = client.get("/lineage/impact/unknown.node")
    assert response.status_code == 200
    assert response.json()["affected"] == []


# ---------------------------------------------------------------------------
# Quality endpoints
# ---------------------------------------------------------------------------

def test_quality_results_roundtrip(client: TestClient):
    result = {"id": "qr-1", "check_name": "not_null", "table": "orders", "status": "pass", "score": 1.0}
    created = client.post("/quality/results", json=result)
    assert created.status_code == 201
    assert created.json() == {"id": "qr-1", "status": "created"}

    response = client.get("/quality/results")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["id"] == "qr-1"


# ---------------------------------------------------------------------------
# Strategy / OpenAPI
# ---------------------------------------------------------------------------

def test_enterprise_backlog_route(client: TestClient):
    response = client.get("/strategy/enterprise-backlog")
    assert response.status_code == 200
    assert "backlog" in response.json()


def test_openapi_docs_available(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/rules" in paths
    assert "/quality/results" in paths


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------

def test_auth_required_returns_401_without_token(client_with_auth: TestClient):
    response = client_with_auth.get("/rules")
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized - valid Bearer token required"}


def test_auth_accepted_with_valid_token(client_with_auth: TestClient):
    response = client_with_auth.get("/rules", headers=_auth("test-secret-token"))
    assert response.status_code == 200


def test_auth_rejected_with_wrong_token(client_with_auth: TestClient):
    response = client_with_auth.get("/rules", headers=_auth("wrong-token"))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Structured error responses
# ---------------------------------------------------------------------------

def test_unknown_route_returns_404(client: TestClient):
    response = client.get("/no-such-endpoint")
    assert response.status_code == 404
    assert response.json() == {"error": "Not found"}


def test_method_not_allowed_returns_structured_error(client: TestClient):
    response = client.put("/rules")
    assert response.status_code == 405
    assert response.json() == {"error": "Method not allowed"}
