from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from services.incident_manager.automation.catalogue import CATALOGUE
from services.incident_manager.automation.contracts import ApprovalState
from services.incident_manager.automation.coordinator import AutomationCoordinator, Expired, PolicyDenied
from services.incident_manager.automation.elasticsearch_repository import ElasticsearchAutomationRepository
from services.incident_manager.automation.repository import Conflict, InMemoryAutomationRepository


class ApprovalRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)
    impact: str = Field(min_length=1, max_length=1000)


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment: str = Field(default="", max_length=1000)


class ExecutionRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=1, max_length=100)
    approval_id: str | None = Field(default=None, max_length=100)


def actor(request: Request) -> str:
    subject = getattr(getattr(request.state, "principal", None), "subject", None)
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(401, "Authenticated principal is required")
    return subject


def permissions(request: Request) -> set[str]:
    principal = getattr(request.state, "principal", None)
    return {str(value) for value in getattr(principal, "permissions", ())}


def create_incident_automation_router(auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/incident-automation", tags=["incident-automation"], dependencies=[Depends(auth_dependency)]
    )

    def repository(request: Request):
        configured = getattr(request.app.state, "incident_automation_repository", None)
        if configured is not None:
            return configured
        incident_repo = request.app.state.incident_manager.repo
        if hasattr(incident_repo, "client"):
            configured = ElasticsearchAutomationRepository(incident_repo.client)
        else:
            # Only development/test composition may use the process-local adapter.
            configured = InMemoryAutomationRepository()
        request.app.state.incident_automation_repository = configured
        return configured

    @router.get("/catalog")
    async def catalog() -> dict[str, Any]:
        return {
            "name": "dataobs-safe-remediation",
            "version": "1.0.0",
            "hash": CATALOGUE.hash,
            "items": [
                {
                    **asdict(item),
                    "payload_model": item.payload_model.__name__,
                    "risk": item.risk.value,
                    "provider_state": "not_configured" if not item.execution_enabled else "ready",
                    "disabled_reason": None if item.execution_enabled else "executor_not_configured",
                }
                for item in CATALOGUE.list()
            ],
        }

    @router.get("/catalog/{action_type}")
    async def catalog_item(action_type: str) -> dict[str, Any]:
        try:
            item = CATALOGUE.require(action_type)
        except ValueError as exc:
            raise HTTPException(404, "Action not found") from exc
        return {
            **asdict(item),
            "payload_model": item.payload_model.__name__,
            "risk": item.risk.value,
            "catalogue_hash": CATALOGUE.hash,
        }

    @router.post("/approvals", status_code=201)
    async def request_approval(
        body: ApprovalRequestBody,
        request: Request,
        environment: str,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        repo=Depends(repository),
    ):
        preview = repo.get_preview(request.state.tenant_id, environment, body.preview_id)
        if not preview:
            raise HTTPException(404, "Preview not found")
        try:
            return (
                AutomationCoordinator(repo)
                .request_approval(
                    preview,
                    requester=actor(request),
                    idempotency_key=idempotency_key,
                    reason=body.reason,
                    impact=body.impact,
                )
                .model_dump(mode="json")
            )
        except Expired as exc:
            raise HTTPException(410, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.get("/approvals/{approval_id}")
    async def get_approval(approval_id: str, request: Request, environment: str, repo=Depends(repository)):
        item = repo.get_approval(request.state.tenant_id, environment, approval_id)
        if not item:
            raise HTTPException(404, "Approval not found")
        return item.model_dump(mode="json")

    async def decide(approval_id: str, body: DecisionBody, request: Request, environment: str, approve: bool, repo):
        try:
            return (
                AutomationCoordinator(repo)
                .decide_approval(
                    request.state.tenant_id,
                    environment,
                    approval_id,
                    actor=actor(request),
                    permissions=permissions(request),
                    approve=approve,
                    comment=body.comment,
                    request_id=request.state.request_id,
                )
                .model_dump(mode="json")
            )
        except KeyError as exc:
            raise HTTPException(404, "Approval not found") from exc
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except Expired as exc:
            raise HTTPException(410, str(exc)) from exc
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.post("/approvals/{approval_id}/approve")
    async def approve(
        approval_id: str, body: DecisionBody, request: Request, environment: str, repo=Depends(repository)
    ):
        return await decide(approval_id, body, request, environment, True, repo)

    @router.post("/approvals/{approval_id}/reject")
    async def reject(
        approval_id: str, body: DecisionBody, request: Request, environment: str, repo=Depends(repository)
    ):
        return await decide(approval_id, body, request, environment, False, repo)

    @router.get("/executions/{execution_id}")
    async def get_execution(execution_id: str, request: Request, environment: str, repo=Depends(repository)):
        item = repo.get_execution(request.state.tenant_id, environment, execution_id)
        if not item:
            raise HTTPException(404, "Execution not found")
        return item.model_dump(mode="json")

    @router.post("/executions", status_code=201)
    async def create_execution(
        body: ExecutionRequestBody,
        request: Request,
        environment: str,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        repo=Depends(repository),
    ):
        preview = repo.get_preview(request.state.tenant_id, environment, body.preview_id)
        if not preview:
            raise HTTPException(404, "Preview not found")
        try:
            from services.incident_manager.automation.targets import ActionTarget, BoundedActionTargetResolver

            resolver = getattr(request.app.state, "action_target_resolver", None)
            if not isinstance(resolver, BoundedActionTargetResolver):
                raise HTTPException(503, "Authoritative target resolver is not configured")
            incident = request.app.state.incident_manager.repo.get_incident(
                request.state.tenant_id, preview.incident_id, environment
            )
            if incident is None:
                raise HTTPException(404, "Incident not found")
            current = resolver.reload(
                tenant_id=request.state.tenant_id,
                environment=environment,
                target=ActionTarget(preview.target["type"], preview.target["id"], preview.target["revision"]),
            )
            return (
                AutomationCoordinator(repo)
                .queue_execution(
                    preview,
                    actor=actor(request),
                    idempotency_key=idempotency_key,
                    current_incident_revision=f"{incident.seq_no}:{incident.primary_term}",
                    current_target_revision=current.revision,
                    approval_id=body.approval_id,
                    request_id=request.state.request_id,
                )
                .model_dump(mode="json")
            )
        except Expired as exc:
            raise HTTPException(410, str(exc)) from exc
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except PolicyDenied as exc:
            status = 503 if "not configured" in str(exc) else 422
            raise HTTPException(status, str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(409, "Authoritative target changed or is unavailable") from exc

    return router
