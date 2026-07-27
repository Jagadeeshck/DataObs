from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from src.api.app import StoreBundle, create_app
from src.config.settings import (
    APISettings,
    AppSettings,
    AuthSettings,
    ElasticsearchSettings,
    ObservabilitySettings,
    RuntimeSettings,
    TenantSettings,
)


class _FakeStore:
    def __init__(self) -> None:
        self.rules = {
            "r1": {
                "rule_id": "r1",
                "dataset": "orders",
                "enabled": True,
                "severity": "high",
                "check_type": "null_check",
            },
            "r2": {
                "rule_id": "r2",
                "dataset": "payments",
                "enabled": False,
                "severity": "low",
                "check_type": "range_check",
            },
        }
        self.results = {
            "q1": {
                "id": "q1",
                "table": "orders",
                "status": "pass",
                "dataset": "d1",
                "check_type": "null_check",
                "severity": "high",
                "run_id": "run-1",
            },
            "q2": {
                "id": "q2",
                "table": "orders",
                "status": "fail",
                "dataset": "d1",
                "check_type": "range_check",
                "severity": "low",
                "run_id": "run-2",
            },
            "q3": {
                "id": "q3",
                "table": "payments",
                "status": "pass",
                "dataset": "d2",
                "check_type": "null_check",
                "severity": "high",
                "run_id": "run-2",
            },
        }

    def get_all_rules(self, **kwargs):
        return list(self.rules.values())

    def add_rule(self, rule):
        self.rules[rule.get("rule_id", "rnew")] = rule
        return rule.get("rule_id", "rnew")

    def delete_rule(self, rule_id):
        return self.rules.pop(rule_id, None) is not None

    def save_quality_result(self, result):
        self.results[result.get("id", "new")] = result
        return result.get("id", "new")

    def list_quality_results(self, **kwargs):
        return list(self.results.values())

    def get_all_nodes(self, **kwargs):
        return [{"node_id": "n1", "type": "table", "dataset": "d1"}, {"node_id": "n2", "type": "job", "dataset": "d2"}]

    def get_all_edges(self, **kwargs):
        return [
            {"source_node_id": "n1", "target_node_id": "n2", "relation": "feeds"},
            {"source_node_id": "n2", "target_node_id": "n3", "relation": "feeds"},
        ]

    def get_downstream_impact(self, node_id, depth=5):
        return ["n2"]


@pytest.fixture()
def client() -> TestClient:
    app = create_app(
        settings=AppSettings(
            runtime=RuntimeSettings(env="test"),
            api=APISettings(),
            elasticsearch=ElasticsearchSettings(),
            auth=AuthSettings(api_token="t", allow_unauthenticated_dev=False),
            tenant=TenantSettings(),
            observability=ObservabilitySettings(),
            store_backend="memory",
        ),
        store_bundle=StoreBundle(store=_FakeStore()),
    )
    return TestClient(app)


def _auth() -> Dict[str, str]:
    return {"Authorization": "Bearer t"}


def test_request_id_round_trip(client: TestClient):
    r = client.get("/rules", headers={**_auth(), "X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"


def test_request_id_generated(client: TestClient):
    r = client.get("/rules", headers=_auth())
    assert r.headers.get("X-Request-ID")


def test_401_structured_error_and_request_id(client: TestClient):
    r = client.get("/rules")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"
    assert r.json()["request_id"]


def test_404_structured_error_and_request_id(client: TestClient):
    r = client.get("/missing", headers=_auth())
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    assert r.json()["request_id"]


def test_422_structured_error_and_request_id(client: TestClient):
    r = client.post("/rules", headers=_auth(), json={"enabled": "oops"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_quality_results_pagination_and_filters(client: TestClient):
    r = client.get("/quality/results?limit=1&offset=1&table=orders&status=pass", headers=_auth())
    assert r.status_code == 200
    assert "pagination" in r.json()


def test_rules_pagination_and_filtering(client: TestClient):
    r = client.get("/rules?limit=1&offset=0&dataset=orders", headers=_auth())
    assert r.status_code == 200
    assert r.json()["pagination"]["limit"] == 1


def test_lineage_nodes_edges_pagination(client: TestClient):
    rn = client.get("/lineage/nodes?limit=1&offset=0", headers=_auth())
    re = client.get("/lineage/edges?limit=1&offset=0", headers=_auth())
    assert rn.status_code == 200 and re.status_code == 200


def test_limit_max_enforced(client: TestClient):
    r = client.get("/rules?limit=1001", headers=_auth())
    assert r.status_code == 422


def test_negative_offset_rejected(client: TestClient):
    r = client.get("/rules?offset=-1", headers=_auth())
    assert r.status_code == 422
