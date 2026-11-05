"""Regression tests for B20: run action authorization reads the Principal dataclass.

The eligibility/action handlers previously called ``request.state.principal.get(...)``
on a frozen ``Principal`` dataclass (no ``.get``), producing an HTTP 500 under real
authentication. These tests pin the corrected behaviour: authority is derived from
``principal.permissions`` (``Permission`` frozenset), preserving the original scope
intent (``jobs:execute``/``workflows:execute`` grant execution; ``workflows:approve``
downgrades the pending-approval gate).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.run_routes import create_run_router
from src.security.models import Principal
from src.security.permissions import Permission


class _Store:
    def __init__(self) -> None:
        self._dataobs_job_runs = {
            "r1": {
                "run_id": "r1",
                "tenant_id": "tenant-alpha",
                "environment": "staging",
                "state": "succeeded",
            }
        }


class _Service:
    def __init__(self) -> None:
        self.store = _Store()

    def get_job_run(self, run_id: str) -> dict[str, Any] | None:
        return self.store._dataobs_job_runs.get(run_id)


def _principal(*permissions: Permission) -> Principal:
    return Principal(
        subject="user-1",
        issuer="https://issuer.example",
        principal_type="user",
        permissions=frozenset(permissions),
    )


def _client(principal: Principal) -> TestClient:
    service = _Service()

    def service_dependency() -> _Service:
        return service

    def auth_dependency(request: Request) -> None:
        request.state.principal = principal
        request.state.tenant_id = "tenant-alpha"
        request.state.environment = "staging"

    app = FastAPI()
    app.include_router(create_run_router(service_dependency, auth_dependency))
    return TestClient(app)


def test_eligibility_executor_is_eligible_and_not_pending_when_approver():
    client = _client(_principal(Permission.JOBS_EXECUTE, Permission.WORKFLOWS_APPROVE))
    resp = client.get("/api/v1/runs/r1/action-eligibility")
    assert resp.status_code == 200
    body = resp.json()
    assert body["eligible"] is True
    assert body["approval_required"] is False
    assert body["reason"] is None
    assert "request_rerun" in body["actions"]


def test_eligibility_executor_without_approve_requires_approval():
    client = _client(_principal(Permission.WORKFLOWS_EXECUTE))
    body = client.get("/api/v1/runs/r1/action-eligibility").json()
    assert body["eligible"] is True
    assert body["approval_required"] is True


def test_eligibility_without_execute_is_not_eligible():
    client = _client(_principal(Permission.JOBS_READ))
    body = client.get("/api/v1/runs/r1/action-eligibility").json()
    assert body["eligible"] is False
    assert body["actions"] == []
    assert body["reason"] == "permission_denied"


def test_action_requires_execute_permission():
    client = _client(_principal(Permission.JOBS_READ))
    resp = client.post(
        "/api/v1/runs/r1/actions",
        json={"action": "request_rerun"},
        headers={"Idempotency-Key": "k1"},
    )
    assert resp.status_code == 403


def test_action_accepted_for_approver_pending_for_executor():
    executor = _client(_principal(Permission.JOBS_EXECUTE))
    pending = executor.post(
        "/api/v1/runs/r1/actions",
        json={"action": "request_rerun"},
        headers={"Idempotency-Key": "k-exec"},
    )
    assert pending.status_code == 202
    assert pending.json()["status"] == "pending_approval"

    approver = _client(_principal(Permission.JOBS_EXECUTE, Permission.WORKFLOWS_APPROVE))
    accepted = approver.post(
        "/api/v1/runs/r1/actions",
        json={"action": "request_rerun"},
        headers={"Idempotency-Key": "k-appr"},
    )
    assert accepted.status_code == 202
    assert accepted.json()["status"] == "accepted"
