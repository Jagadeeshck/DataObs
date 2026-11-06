"""Regression tests for B20: stream list routes read the Principal dataclass.

The in-route ``scope()`` guard previously called ``request.state.principal.get("scopes")``
on a frozen ``Principal`` (no ``.get``), 500-ing every stream list route under real
authentication. These tests pin the corrected behaviour: the guard checks
``principal.permissions`` for the required ``Permission`` and preserves the original
admin bypass via the authoritative admin roles (``platform_admin``/``tenant_admin``).

``StreamRepository.search`` is stubbed so the test exercises the authorization guard
without depending on a live Elasticsearch backend.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api import stream_routes
from src.api.stream_routes import READ_SCOPE, create_stream_router
from src.security.models import Principal
from src.security.permissions import Permission


class _FakeEs:
    es: Any = object()


def _principal(*, permissions: frozenset[Permission] = frozenset(), roles: frozenset[str] = frozenset()) -> Principal:
    return Principal(
        subject="user-1",
        issuer="https://issuer.example",
        principal_type="user",
        permissions=permissions,
        roles=roles,
    )


def _client(principal: Principal, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(stream_routes.StreamRepository, "search", lambda *a, **k: [])

    def get_es() -> _FakeEs:
        return _FakeEs()

    def require_auth(request: Request) -> None:
        request.state.principal = principal
        request.state.tenant_id = "tenant-alpha"
        request.state.environment = "staging"
        request.state.request_id = "req-1"

    app = FastAPI()
    app.include_router(create_stream_router(get_es, require_auth))
    return TestClient(app)


def test_read_scope_values_are_real_permissions():
    # The route must map scope strings to Permission members the Principal carries,
    # never to invented scope fields.
    assert set(READ_SCOPE.values()) <= set(Permission)
    assert READ_SCOPE["streams"] is Permission.STREAMS_READ


def test_streams_list_allows_principal_with_streams_read(monkeypatch):
    client = _client(_principal(permissions=frozenset({Permission.STREAMS_READ})), monkeypatch)
    resp = client.get("/api/v1/streams", params={"environment": "staging", "page_size": 2})
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_streams_list_allows_admin_role_bypass(monkeypatch):
    # Admin roles carry every permission; the explicit bypass is preserved.
    client = _client(_principal(roles=frozenset({"platform_admin"})), monkeypatch)
    resp = client.get("/api/v1/streams", params={"environment": "staging", "page_size": 2})
    assert resp.status_code == 200


def test_streams_list_denies_without_permission(monkeypatch):
    client = _client(_principal(permissions=frozenset({Permission.JOBS_READ})), monkeypatch)
    resp = client.get("/api/v1/streams", params={"environment": "staging", "page_size": 2})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "insufficient_scope"
