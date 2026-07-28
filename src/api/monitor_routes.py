"""Typed monitoring API. Development authentication is not production authorization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from packages.domain_model.monitor import MonitorDefinition, MonitorState
from services.monitoring.capabilities import capability_documents, validate_monitor_definition
from services.monitoring.repository import ConsistencyError, VersionConflict

router = APIRouter(prefix="/api/v1", tags=["monitoring"])


class MonitorPage(BaseModel):
    items: list[MonitorDefinition]
    next_cursor: str | None = None


class MonitorPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: MonitorState | None = None
    etag: str


class SuppressionRequest(BaseModel):
    starts_at: str
    ends_at: str
    reason: str = Field(min_length=1, max_length=500)
    approval_reference: str = Field(min_length=1, max_length=200)


class TransitionRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)


class RunRequest(BaseModel):
    scheduled_for: datetime | None = None


def repo(request: Request):
    value = getattr(request.app.state, "monitor_repository", None)
    if value is None:
        raise HTTPException(503, "monitor runtime repository unavailable")
    return value


def scope(request):
    return request.state.tenant_id, getattr(request.app.state.settings, "environment", "default")


def translate(exc):
    if isinstance(exc, VersionConflict):
        raise HTTPException(412, "monitor changed concurrently")
    if isinstance(exc, ConsistencyError):
        raise HTTPException(409, "immutable monitor history diverged")
    raise exc


@router.get("/quality/capabilities")
def capabilities():
    return {"schema_version": "v1", "items": capability_documents()}


@router.get("/quality/monitors", response_model=MonitorPage)
@router.get("/monitors", response_model=MonitorPage, deprecated=True)
def list_monitors(request: Request, limit: int = Query(50, ge=1, le=200), cursor: str | None = None):
    return {"items": repo(request).list_monitors(*scope(request), limit=limit, cursor=cursor)}


@router.post("/quality/monitors", response_model=MonitorDefinition, status_code=201)
@router.post("/monitors", response_model=MonitorDefinition, status_code=201, deprecated=True)
def create_monitor(body: MonitorDefinition, request: Request, response: Response):
    tenant, environment = scope(request)
    if (body.tenant_id, body.environment) != (tenant, environment):
        raise HTTPException(403, "tenant or environment override is forbidden")
    try:
        validate_monitor_definition(body)
        value = repo(request).create_monitor(body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        translate(exc)
    response.headers["ETag"] = value.etag
    return value


@router.get("/quality/monitors/{monitor_id}", response_model=MonitorDefinition)
@router.get("/monitors/{monitor_id}", response_model=MonitorDefinition, deprecated=True)
def get_monitor(monitor_id: str, request: Request, response: Response):
    value = repo(request).get_monitor(*scope(request), monitor_id)
    if value is None:
        raise HTTPException(404, "monitor not found")
    response.headers["ETag"] = value.etag
    return value


@router.patch("/quality/monitors/{monitor_id}", response_model=MonitorDefinition)
@router.patch("/monitors/{monitor_id}", response_model=MonitorDefinition, deprecated=True)
def patch_monitor(monitor_id: str, body: MonitorPatch, request: Request, if_match: str | None = Header(None)):
    if not if_match:
        raise HTTPException(428, "If-Match is required")
    value = repo(request).get_monitor(*scope(request), monitor_id)
    if value is None:
        raise HTTPException(404, "monitor not found")
    updated = value.model_copy(
        update={"state": body.state or value.state, "etag": body.etag, "revision": value.revision + 1}
    )
    try:
        return repo(request).update_monitor(updated, expected_etag=if_match)
    except Exception as exc:
        translate(exc)


def state_route(state):
    def transition(monitor_id: str, request: Request, if_match: str | None = Header(None)):
        if not if_match:
            raise HTTPException(428, "If-Match is required")
        value = repo(request).get_monitor(*scope(request), monitor_id)
        if value is None:
            raise HTTPException(404, "monitor not found")
        return repo(request).update_monitor(
            value.model_copy(update={"state": state, "revision": value.revision + 1}), expected_etag=if_match
        )

    return transition


for prefix in ("/monitors", "/quality/monitors"):
    router.add_api_route(f"{prefix}/{{monitor_id}}/enable", state_route(MonitorState.ENABLED), methods=["POST"])
    router.add_api_route(f"{prefix}/{{monitor_id}}/disable", state_route(MonitorState.DISABLED), methods=["POST"])


@router.post("/quality/monitors/{monitor_id}/archive")
@router.delete("/quality/monitors/{monitor_id}")
@router.post("/monitors/{monitor_id}/archive", deprecated=True)
def archive(monitor_id: str, request: Request, if_match: str | None = Header(None)):
    if not if_match:
        raise HTTPException(428, "If-Match is required")
    return repo(request).archive_monitor(*scope(request), monitor_id, expected_etag=if_match)


@router.get("/quality/monitors/{monitor_id}/history")
@router.get("/monitors/{monitor_id}/history", deprecated=True)
def history(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    return {"items": repo(request).list_definition_history(*scope(request), monitor_id, limit=limit)}


@router.get("/quality/monitors/{monitor_id}/observations")
@router.get("/monitors/{monitor_id}/observations", deprecated=True)
def observations(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    from datetime import datetime, timezone

    return {"items": repo(request).history(*scope(request), monitor_id, datetime.now(timezone.utc), limit)}


@router.get("/quality/monitors/{monitor_id}/baselines")
@router.get("/monitors/{monitor_id}/baselines", deprecated=True)
def baselines(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    return {"items": repo(request).list_baseline_versions(*scope(request), monitor_id, limit=limit)}


@router.post("/quality/monitors/{monitor_id}/baselines/reset")
@router.post("/monitors/{monitor_id}/baselines/reset", deprecated=True)
def reset_baseline(
    monitor_id: str, body: TransitionRequest, request: Request, reason: str = Query(..., min_length=1, max_length=500)
):
    return repo(request).reset_baseline(*scope(request), monitor_id, actor=body.actor, reason=reason)


@router.get("/quality/monitors/{monitor_id}/evaluations")
@router.get("/monitors/{monitor_id}/evaluations", deprecated=True)
def evaluations(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    return {"items": repo(request).list_evaluations(*scope(request), monitor_id, limit=limit)}


@router.get("/quality/monitors/{monitor_id}/findings")
@router.get("/monitors/{monitor_id}/findings", deprecated=True)
def findings(monitor_id: str, request: Request):
    return {"items": repo(request).list_findings(*scope(request), monitor_id, limit=100)}


@router.get("/quality/monitors/{monitor_id}/incidents")
def incidents(monitor_id: str, request: Request):
    findings = repo(request).list_findings(*scope(request), monitor_id, limit=100)
    return {
        "items": [
            {"incident_id": finding.incident_id, "finding_id": finding.finding_id}
            for finding in findings
            if finding.incident_id
        ]
    }


@router.get("/quality/monitors/{monitor_id}/suppressions")
@router.get("/monitors/{monitor_id}/suppressions", deprecated=True)
def suppressions(monitor_id: str, request: Request):
    from datetime import datetime, timezone

    return {"items": repo(request).get_active_suppressions(*scope(request), monitor_id, datetime.now(timezone.utc))}


@router.post("/quality/monitors/{monitor_id}/suppressions", status_code=201)
def create_suppression(monitor_id: str, body: SuppressionRequest, request: Request):
    tenant, environment = scope(request)
    starts_at, ends_at = datetime.fromisoformat(body.starts_at), datetime.fromisoformat(body.ends_at)
    if ends_at <= starts_at or (ends_at - starts_at).days > 31:
        raise HTTPException(422, "suppression must have a positive duration of at most 31 days")
    principal = request.state.principal
    return repo(request).create_suppression(
        {
            "id": str(uuid4()),
            "monitor_id": monitor_id,
            "tenant_id": tenant,
            "environment": environment,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "reason": body.reason,
            "approved_by": body.approval_reference,
            "created_by": principal.subject,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "revision": 1,
            "state": "active",
        }
    )


@router.post("/quality/monitors/{monitor_id}/run", status_code=202)
def run_monitor(
    monitor_id: str,
    body: RunRequest,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    tenant, environment = scope(request)
    monitor = repo(request).get_monitor(tenant, environment, monitor_id)
    if monitor is None:
        raise HTTPException(404, "monitor not found")
    if monitor.state not in {MonitorState.ENABLED, MonitorState.ACTIVE, MonitorState.LEARNING}:
        raise HTTPException(409, "only enabled monitors can be run")
    execution_id = repo(request).request_execution(
        tenant,
        environment,
        monitor_id,
        scheduled_for=body.scheduled_for or datetime.now(timezone.utc),
        idempotency_key=idempotency_key,
    )
    return {"execution_id": execution_id, "status": "queued"}


@router.get("/quality/recommendations")
@router.get("/monitor-recommendations", deprecated=True)
def recommendations(request: Request, limit: int = Query(50, ge=1, le=200)):
    return {"items": repo(request).list_recommendations(*scope(request), limit=limit)}


@router.post("/quality/recommendations/{recommendation_id}/{action}")
@router.post("/monitor-recommendations/{recommendation_id}/{action}", deprecated=True)
def recommendation_transition(
    recommendation_id: str, action: Literal["accept", "reject", "defer"], body: TransitionRequest, request: Request
):
    return repo(request).transition_recommendation(
        *scope(request),
        recommendation_id,
        {"accept": "accepted", "reject": "rejected", "defer": "deferred"}[action],
        actor=body.actor,
    )


@router.get("/quality/coverage")
@router.get("/monitor-coverage", deprecated=True)
def coverage(request: Request):
    return repo(request).get_coverage(*scope(request)) or {"state": "unknown"}


@router.get("/quality/runtime/health")
@router.get("/monitor-runtime/health", deprecated=True)
def runtime_health(request: Request):
    health = getattr(request.app.state, "monitor_runtime_health", None)
    if health is None:
        raise HTTPException(503, "monitor runtime unavailable")
    return health.snapshot()


@router.get("/quality/runtime/backlog")
@router.get("/monitor-runtime/backlog", deprecated=True)
def backlog(request: Request):
    health = getattr(request.app.state, "monitor_runtime_health", None)
    if health is None:
        raise HTTPException(503, "monitor runtime unavailable")
    return {"backlog": health.backlog}
