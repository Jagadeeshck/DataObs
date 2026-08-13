"""Typed Team 2 dbt intelligence API. Owner: Team 2; parent: Jobs."""

from __future__ import annotations

from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from integrations.dbt.errors import DbtArtifactError


class ArtifactIngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1, max_length=512)
    project_name: str = Field(min_length=1, max_length=512)
    artifact_type: Literal["manifest", "run_results", "catalog", "freshness"]
    artifact: dict[str, Any]
    repository_ref: str = Field(default="unknown", max_length=1024)
    commit_sha: str = Field(default="unknown", max_length=128)


def create_dbt_router(service_dependency: Callable[..., Any], auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/dbt", tags=["dbt"], dependencies=[Depends(auth_dependency)])

    @router.post("/artifacts", status_code=202)
    def ingest(payload: ArtifactIngestionRequest, request: Request, service: Any = Depends(service_dependency)):
        try:
            result = service.ingest(
                request.state.tenant_id,
                request.state.environment,
                payload.project_id,
                payload.project_name,
                payload.artifact_type,
                payload.artifact,
                repository_ref=payload.repository_ref,
                commit_sha=payload.commit_sha,
            )
            return {
                "event_id": result["event_id"],
                "status": result["status"],
                "artifact_fingerprint": result["artifact"].envelope.artifact_fingerprint,
            }
        except DbtArtifactError as exc:
            raise HTTPException(422, {"code": exc.code, "message": exc.safe_message, "details": exc.details}) from exc

    @router.get("/overview")
    @router.get("/projects")
    def projects(request: Request, service: Any = Depends(service_dependency), limit: int = Query(100, ge=1, le=1000)):
        return {"items": service.repository.list_projects(request.state.tenant_id, request.state.environment, limit)}

    @router.get("/projects/{project_id}")
    def project(project_id: str, request: Request, service: Any = Depends(service_dependency)):
        value = service.repository.get_project(request.state.tenant_id, request.state.environment, project_id)
        if not value:
            raise HTTPException(404, "dbt project not found")
        return value

    @router.get("/projects/{project_id}/resources")
    def resources(
        project_id: str,
        request: Request,
        service: Any = Depends(service_dependency),
        resource_type: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
    ):
        return {
            "items": service.repository.list_resources(
                request.state.tenant_id, request.state.environment, project_id, resource_type, limit
            )
        }

    for path, kind in (("tests", "test"), ("semantic", "semantic_model"), ("freshness", "source")):

        async def listing(
            project_id: str,
            request: Request,
            service: Any = Depends(service_dependency),
            limit: int = Query(100, ge=1, le=1000),
            resource_kind: str = kind,
        ):
            return {
                "items": service.repository.list_resources(
                    request.state.tenant_id, request.state.environment, project_id, resource_kind, limit
                )
            }

        router.add_api_route(f"/projects/{{project_id}}/{path}", listing, methods=["GET"], name=f"dbt_project_{path}")
    return router
