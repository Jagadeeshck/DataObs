from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

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
    model_config = ConfigDict(extra="forbid")
    action_type: str = Field(max_length=80)
    incident_revision: str = Field(min_length=1, max_length=120)
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
            from services.incident_manager.automation.coordinator import AutomationCoordinator
            from services.incident_manager.automation.elasticsearch_repository import ElasticsearchAutomationRepository
            from services.incident_manager.automation.preview import PreviewService
            from services.incident_manager.automation.repository import InMemoryAutomationRepository

            detail = workbench.detail(request.state.tenant_id, environment, incident_id, request.state.request_id)
            if detail["revision"] != body.incident_revision:
                raise VersionConflict("incident revision changed")
            repo = getattr(request.app.state, "incident_automation_repository", None)
            if repo is None:
                incident_repo = request.app.state.incident_manager.repo
                repo = (
                    ElasticsearchAutomationRepository(incident_repo.client)
                    if hasattr(incident_repo, "client")
                    else InMemoryAutomationRepository()
                )
                request.app.state.incident_automation_repository = repo
            result = PreviewService().create(
                tenant_id=request.state.tenant_id,
                environment=environment,
                incident_id=incident_id,
                incident_revision=body.incident_revision,
                incident_state=detail["state"],
                severity=detail["severity"],
                affected_asset_count=len(detail["affected_assets"]),
                action_type=body.action_type,
                payload=body.payload,
                actor=authenticated_actor(request),
                request_id=request.state.request_id,
            )
            return AutomationCoordinator(repo).save_preview(result).model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Incident not found") from exc
        except VersionConflict as exc:
            raise HTTPException(status_code=409, detail="Incident changed; create a new preview") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
