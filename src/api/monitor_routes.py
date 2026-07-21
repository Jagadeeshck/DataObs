"""Typed monitoring API. Development authentication is not production authorization."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from packages.domain_model.monitor import MonitorDefinition, MonitorState
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


@router.get("/monitors", response_model=MonitorPage)
def list_monitors(request: Request, limit: int = Query(50, ge=1, le=200), cursor: str | None = None):
    return {"items": repo(request).list_monitors(*scope(request), limit=limit, cursor=cursor)}


@router.post("/monitors", response_model=MonitorDefinition, status_code=201)
def create_monitor(body: MonitorDefinition, request: Request, response: Response):
    tenant, environment = scope(request)
    if (body.tenant_id, body.environment) != (tenant, environment):
        raise HTTPException(403, "tenant or environment override is forbidden")
    try:
        value = repo(request).create_monitor(body)
    except Exception as exc:
        translate(exc)
    response.headers["ETag"] = value.etag
    return value


@router.get("/monitors/{monitor_id}", response_model=MonitorDefinition)
def get_monitor(monitor_id: str, request: Request, response: Response):
    value = repo(request).get_monitor(*scope(request), monitor_id)
    if value is None:
        raise HTTPException(404, "monitor not found")
    response.headers["ETag"] = value.etag
    return value


@router.patch("/monitors/{monitor_id}", response_model=MonitorDefinition)
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


router.add_api_route("/monitors/{monitor_id}/enable", state_route(MonitorState.ENABLED), methods=["POST"])
router.add_api_route("/monitors/{monitor_id}/disable", state_route(MonitorState.DISABLED), methods=["POST"])


@router.post("/monitors/{monitor_id}/archive")
def archive(monitor_id: str, request: Request, if_match: str | None = Header(None)):
    if not if_match:
        raise HTTPException(428, "If-Match is required")
    return repo(request).archive_monitor(*scope(request), monitor_id, expected_etag=if_match)


@router.get("/monitors/{monitor_id}/history")
def history(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    return {"items": repo(request).list_definition_history(*scope(request), monitor_id, limit=limit)}


@router.get("/monitors/{monitor_id}/observations")
def observations(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    from datetime import datetime, timezone

    return {"items": repo(request).history(*scope(request), monitor_id, datetime.now(timezone.utc), limit)}


@router.get("/monitors/{monitor_id}/baselines")
def baselines(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    return {"items": repo(request).list_baseline_versions(*scope(request), monitor_id, limit=limit)}


@router.post("/monitors/{monitor_id}/baselines/reset")
def reset_baseline(
    monitor_id: str, body: TransitionRequest, request: Request, reason: str = Query(..., min_length=1, max_length=500)
):
    return repo(request).reset_baseline(*scope(request), monitor_id, actor=body.actor, reason=reason)


@router.get("/monitors/{monitor_id}/evaluations")
def evaluations(monitor_id: str, request: Request, limit: int = Query(50, ge=1, le=200)):
    return {"items": repo(request).list_evaluations(*scope(request), monitor_id, limit=limit)}


@router.get("/monitors/{monitor_id}/findings")
def findings(monitor_id: str, request: Request):
    return {"items": [], "status": "incident-manager-projection"}


@router.get("/monitors/{monitor_id}/suppressions")
def suppressions(monitor_id: str, request: Request):
    from datetime import datetime, timezone

    return {"items": repo(request).get_active_suppressions(*scope(request), monitor_id, datetime.now(timezone.utc))}


@router.get("/monitor-recommendations")
def recommendations(request: Request, limit: int = Query(50, ge=1, le=200)):
    return {"items": repo(request).list_recommendations(*scope(request), limit=limit)}


@router.post("/monitor-recommendations/{recommendation_id}/{action}")
def recommendation_transition(
    recommendation_id: str, action: Literal["accept", "reject", "defer"], body: TransitionRequest, request: Request
):
    return repo(request).transition_recommendation(
        *scope(request),
        recommendation_id,
        {"accept": "accepted", "reject": "rejected", "defer": "deferred"}[action],
        actor=body.actor,
    )


@router.get("/monitor-coverage")
def coverage(request: Request):
    return repo(request).get_coverage(*scope(request)) or {"state": "unknown"}


@router.get("/monitor-runtime/health")
def runtime_health(request: Request):
    health = getattr(request.app.state, "monitor_runtime_health", None)
    if health is None:
        raise HTTPException(503, "monitor runtime unavailable")
    return health.snapshot()


@router.get("/monitor-runtime/backlog")
def backlog(request: Request):
    health = getattr(request.app.state, "monitor_runtime_health", None)
    if health is None:
        raise HTTPException(503, "monitor runtime unavailable")
    return {"backlog": health.backlog}
