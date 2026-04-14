"""
Integration tests for the DataObs API server (src/api/main.py).

Spins up a real ThreadingHTTPServer on a random port, hits it with urllib,
and tears it down after each test.  No real Elasticsearch is needed \u2014
a fake store is injected via module-level globals.
"""
from __future__ import annotations

import json
import os
import threading
from http.server import ThreadingHTTPServer
from typing import Any, Dict, List
from urllib import request as urllib_request
from urllib.error import HTTPError

import pytest

import src.api.main as api_module
from src.api.main import DataObsHandler


# ---------------------------------------------------------------------------
# Fake stores (no ES required)
# ---------------------------------------------------------------------------

class _FakeRuleStore:
    def __init__(self):
        self._rules: List[Dict[str, Any]] = []

    def add_rule(self, rule: Dict[str, Any]) -> str:
        rule_id = rule.get("rule_id", f"rule-{len(self._rules)+1}")
        rule["rule_id"] = rule_id
        self._rules.append(rule)
        return rule_id

    def get_all_rules(self) -> List[Dict[str, Any]]:
        return list(self._rules)


class _FakeLineageStore:
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        return [{"node_id": "rds.prod.orders", "node_type": "table"}]

    def get_all_edges(self) -> List[Dict[str, Any]]:
        return [{"source_node_id": "rds.prod.source", "target_node_id": "rds.prod.orders"}]

    def get_downstream_impact(self, node_id: str, depth: int = 5) -> List[str]:
        return ["rds.prod.reports"] if node_id == "rds.prod.orders" else []


# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_server():
    """Start the API server on a random port; yield base_url; stop after test."""
    # Inject fake stores + disable auth for most tests
    api_module._rule_store = _FakeRuleStore()
    api_module._lineage_store = _FakeLineageStore()
    api_module._api_token = None  # no auth

    server = ThreadingHTTPServer(("127.0.0.1", 0), DataObsHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()


@pytest.fixture()
def api_server_with_auth():
    """API server with Bearer token auth enabled."""
    api_module._rule_store = _FakeRuleStore()
    api_module._lineage_store = _FakeLineageStore()
    api_module._api_token = "test-secret-token"

    server = ThreadingHTTPServer(("127.0.0.1", 0), DataObsHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(base_url: str, path: str, token: str | None = None) -> tuple[int, dict]:
    req = urllib_request.Request(f"{base_url}{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib_request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except HTTPError as e:
        return e.code, {}


def _post(base_url: str, path: str, body: dict, token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib_request.Request(f"{base_url}{path}", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Content-Length", str(len(data)))
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib_request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except HTTPError as e:
        return e.code, {}


# ---------------------------------------------------------------------------
# Health check (no auth)
# ---------------------------------------------------------------------------

def test_health_check_returns_200(api_server):
    status, body = _get(api_server, "/health")
    assert status == 200
    assert body["status"] == "ok"


def test_health_check_no_auth_required(api_server_with_auth):
    """Health endpoint must be reachable without a token (for load balancers)."""
    status, body = _get(api_server_with_auth, "/health")
    assert status == 200


# ---------------------------------------------------------------------------
# Rules endpoint
# ---------------------------------------------------------------------------

def test_get_rules_returns_empty_list(api_server):
    status, body = _get(api_server, "/rules")
    assert status == 200
    assert body["rules"] == []
    assert body["count"] == 0


def test_post_rule_creates_and_returns_id(api_server):
    rule = {"dataset": "prod.orders", "check_type": "null_check", "severity": "critical"}
    status, body = _post(api_server, "/rules", rule)
    assert status == 201
    assert "rule_id" in body
    assert body["status"] == "created"


def test_post_rule_then_get_returns_it(api_server):
    rule = {"dataset": "prod.orders", "check_type": "row_count", "severity": "high"}
    _post(api_server, "/rules", rule)

    status, body = _get(api_server, "/rules")
    assert status == 200
    assert body["count"] == 1
    assert body["rules"][0]["dataset"] == "prod.orders"


# ---------------------------------------------------------------------------
# Lineage endpoints
# ---------------------------------------------------------------------------

def test_get_lineage_nodes(api_server):
    status, body = _get(api_server, "/lineage/nodes")
    assert status == 200
    assert body["count"] == 1
    assert body["nodes"][0]["node_id"] == "rds.prod.orders"


def test_get_lineage_edges(api_server):
    status, body = _get(api_server, "/lineage/edges")
    assert status == 200
    assert body["count"] == 1


def test_lineage_impact_returns_affected_nodes(api_server):
    status, body = _get(api_server, "/lineage/impact/rds.prod.orders")
    assert status == 200
    assert body["root_node"] == "rds.prod.orders"
    assert "rds.prod.reports" in body["affected"]


def test_lineage_impact_unknown_node_returns_empty(api_server):
    status, body = _get(api_server, "/lineage/impact/unknown.node")
    assert status == 200
    assert body["affected"] == []


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------

def test_auth_required_returns_401_without_token(api_server_with_auth):
    status, _ = _get(api_server_with_auth, "/rules")
    assert status == 401


def test_auth_accepted_with_valid_token(api_server_with_auth):
    status, body = _get(api_server_with_auth, "/rules", token="test-secret-token")
    assert status == 200


def test_auth_rejected_with_wrong_token(api_server_with_auth):
    status, _ = _get(api_server_with_auth, "/rules", token="wrong-token")
    assert status == 401


# ---------------------------------------------------------------------------
# 404 for unknown routes
# ---------------------------------------------------------------------------

def test_unknown_route_returns_404(api_server):
    status, body = _get(api_server, "/no-such-endpoint")
    assert status == 404
