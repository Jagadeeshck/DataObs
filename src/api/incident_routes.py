from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from packages.domain_model.incident import IncidentState
from services.incident_manager.repository import VersionConflict
from services.incident_manager.workbench import CursorMismatch, IncidentWorkbenchService


class Mutation(BaseModel):
    revision: str
    state: IncidentState | None = None
    reason: str | None = Field(default=None, max_length=500)
    owner: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=2000)


class ActionPreview(BaseModel):
    action_type: str = Field(max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)


def authenticated_actor(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    subject = getattr(principal, "subject", None)
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status_code=401, detail="Authenticated principal is required")
    return subject


def create_incident_workbench_router(auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/incident-workbench", tags=["incident-workbench"], dependencies=[Depends(auth_dependency)]
    )

    def service(request: Request) -> IncidentWorkbenchService:
        return IncidentWorkbenchService(request.app.state.incident_manager.repo)

    @router.get("")
    async def inbox(
        request: Request,
        environment: str = Query(min_length=1, max_length=80),
        state: str | None = None,
        severity: str | None = None,
        owner: str | None = None,
        business_service: str | None = None,
        asset: str | None = None,
        search: str = Query("", max_length=200),
        unassigned: bool = False,
        sort: str = Query("recently_observed", pattern="^(newest_opened|recently_observed|severity|occurrence_count)$"),
        page_size: int = Query(25, ge=1, le=100),
        cursor: str | None = None,
        workbench: IncidentWorkbenchService = Depends(service),
    ) -> dict[str, Any]:
        try:
            return workbench.inbox(
                request.state.tenant_id,
                environment,
                filters={
                    "state": state,
                    "severity": severity,
                    "owner": owner,
                    "business_service": business_service,
                    "asset": asset,
                    "search": search,
                    "unassigned": unassigned,
                },
                sort=sort,
                page_size=page_size,
                cursor=cursor,
            )
        except CursorMismatch as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/{incident_id}")
    async def detail(
        incident_id: str, request: Request, environment: str, workbench: IncidentWorkbenchService = Depends(service)
    ) -> dict[str, Any]:
        try:
            return workbench.detail(request.state.tenant_id, environment, incident_id, request.state.request_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Incident not found") from exc

    @router.get("/{incident_id}/timeline")
    async def timeline(
        incident_id: str,
        request: Request,
        environment: str,
        page_size: int = Query(50, ge=1, le=100),
        cursor: str | None = Query(None, max_length=2048),
        workbench: IncidentWorkbenchService = Depends(service),
    ) -> dict[str, Any]:
        try:
            return workbench.timeline(
                request.state.tenant_id, environment, incident_id, page_size=page_size, cursor=cursor
            )
        except CursorMismatch as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid timeline cursor; restart pagination",
            ) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Incident not found") from exc

    @router.post("/{incident_id}/mutations")
    async def mutate(
        incident_id: str,
        body: Mutation,
        request: Request,
        environment: str,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        workbench: IncidentWorkbenchService = Depends(service),
    ) -> dict[str, Any]:
        try:
            return workbench.mutate(
                request.state.tenant_id,
                environment,
                incident_id,
                revision=body.revision,
                actor=authenticated_actor(request),
                request_id=request.state.request_id,
                state=body.state,
                reason=body.reason,
                owner=body.owner,
                comment=body.comment,
                idempotency_key=idempotency_key,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Incident not found") from exc
        except VersionConflict as exc:
            raise HTTPException(
                status_code=409,
                detail={"message": "Incident changed; refresh before retrying", "request_id": request.state.request_id},
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/{incident_id}/actions/preview")
    async def preview(
        incident_id: str,
        body: ActionPreview,
        request: Request,
        environment: str,
        workbench: IncidentWorkbenchService = Depends(service),
    ) -> dict[str, Any]:
        try:
            return workbench.preview(request.state.tenant_id, environment, incident_id, body.action_type, body.payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Incident not found") from exc

    return router
