"""Team 1 stream/pathway reliability HTTP surface."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response

from packages.streaming.reliability import CAPABILITIES, Definition
from services.kafka_observer.reliability_repository import (
    DEFINITIONS,
    DEFINITIONS_READ,
    ElasticsearchReliabilityRepository,
)


def create_reliability_router(get_es: Callable[..., Any], require_auth: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["stream-reliability"], dependencies=[Depends(require_auth)])

    def repository(es: Any = Depends(get_es)) -> ElasticsearchReliabilityRepository:
        return ElasticsearchReliabilityRepository(es.es)

    def scope(request: Request) -> tuple[str, str]:
        environment = request.headers.get("x-dataobs-environment", "production")
        return request.state.tenant_id, environment

    @router.get("/reliability/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "resource_types": [
                {"resource_type": resource, "metrics": list(metrics)} for resource, metrics in CAPABILITIES.items()
            ],
            "operators": ["gt", "gte", "lt", "lte"],
            "missing_data_policies": ["no_data", "breach", "ignore"],
        }

    @router.get("/stream-slos")
    def list_slos(
        request: Request,
        limit: int = Query(50, ge=1, le=200),
        resource_type: str | None = None,
        resource_id: str | None = None,
        metric: str | None = None,
        enabled: bool | None = None,
        owner: str | None = None,
        repo: ElasticsearchReliabilityRepository = Depends(repository),
    ) -> dict[str, Any]:
        tenant, environment = scope(request)
        items = repo.inventory(tenant, environment, size=limit, filters=locals())
        return {"items": items, "next_cursor": None}

    @router.post("/stream-slos", status_code=201)
    def create_slo(
        payload: dict[str, Any],
        request: Request,
        response: Response,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        repo: ElasticsearchReliabilityRepository = Depends(repository),
    ) -> dict[str, Any]:
        tenant, environment = scope(request)
        now = datetime.now(timezone.utc).isoformat()
        identifier = hashlib.sha256(f"{tenant}\0{environment}\0{idempotency_key}".encode()).hexdigest()
        actor = str(request.state.principal.get("sub", "unknown"))
        document = payload | {
            "id": identifier,
            "tenant_id": tenant,
            "environment": environment,
            "enabled": False,
            "revision": 1,
            "created_at": now,
            "updated_at": now,
            "created_actor": actor,
            "updated_actor": actor,
            "schema_version": "v1",
            "next_evaluation_at": now,
        }
        Definition(**{key: document[key] for key in Definition.__dataclass_fields__})
        try:
            repo.es.index(index=DEFINITIONS, id=identifier, document=document, op_type="create", refresh="wait_for")
        except Exception as exc:
            if type(exc).__name__ != "ConflictError":
                raise
        response.headers["ETag"] = '"1"'
        return document

    def get_definition(slo_id: str, request: Request, repo: ElasticsearchReliabilityRepository) -> dict[str, Any]:
        tenant, environment = scope(request)
        try:
            document = repo.es.get(index=DEFINITIONS_READ, id=slo_id)["_source"]
        except Exception as exc:
            raise HTTPException(404, detail={"code": "not_found", "message": "SLO not found"}) from exc
        if document.get("tenant_id") != tenant or document.get("environment") != environment:
            raise HTTPException(404, detail={"code": "not_found", "message": "SLO not found"})
        return document

    @router.get("/stream-slos/{slo_id}")
    def get_slo(
        slo_id: str,
        request: Request,
        response: Response,
        repo: ElasticsearchReliabilityRepository = Depends(repository),
    ) -> dict[str, Any]:
        document = get_definition(slo_id, request, repo)
        response.headers["ETag"] = f'"{document["revision"]}"'
        return document

    @router.patch("/stream-slos/{slo_id}")
    def update_slo(
        slo_id: str,
        payload: dict[str, Any],
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match"),
        repo: ElasticsearchReliabilityRepository = Depends(repository),
    ) -> dict[str, Any]:
        current = get_definition(slo_id, request, repo)
        expected = f'"{current["revision"]}"'
        if if_match is None:
            raise HTTPException(428, detail={"code": "precondition_required", "message": "If-Match is required"})
        if if_match != expected:
            raise HTTPException(412, detail={"code": "revision_conflict", "message": "ETag is stale"})
        protected = {"id", "tenant_id", "environment", "created_at", "created_actor", "revision"}
        updated = current | {key: value for key, value in payload.items() if key not in protected}
        updated["revision"] += 1
        updated["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated["updated_actor"] = str(request.state.principal.get("sub", "unknown"))
        Definition(**{key: updated[key] for key in Definition.__dataclass_fields__})
        repo.es.index(index=DEFINITIONS, id=slo_id, document=updated, refresh="wait_for")
        response.headers["ETag"] = f'"{updated["revision"]}"'
        return updated

    @router.delete("/stream-slos/{slo_id}", status_code=204)
    def delete_slo(
        slo_id: str,
        request: Request,
        if_match: str | None = Header(None, alias="If-Match"),
        repo: ElasticsearchReliabilityRepository = Depends(repository),
    ) -> None:
        current = get_definition(slo_id, request, repo)
        if if_match != f'"{current["revision"]}"':
            raise HTTPException(
                412 if if_match else 428, detail={"code": "revision_conflict", "message": "valid If-Match required"}
            )
        repo.es.delete(index=DEFINITIONS, id=slo_id, refresh="wait_for")

    @router.get("/stream-slos/{slo_id}/evaluations")
    @router.get("/pathway-slos/{slo_id}/evaluations")
    def evaluation_history(
        slo_id: str,
        request: Request,
        limit: int = Query(50, ge=1, le=200),
        repo: ElasticsearchReliabilityRepository = Depends(repository),
    ) -> dict[str, Any]:
        definition = Definition(
            **{key: get_definition(slo_id, request, repo)[key] for key in Definition.__dataclass_fields__}
        )
        return {"items": repo.evaluations(definition, limit), "next_cursor": None}

    @router.get("/stream-slos/{slo_id}/status")
    @router.get("/pathway-slos/{slo_id}/status")
    def current_status(
        slo_id: str, request: Request, repo: ElasticsearchReliabilityRepository = Depends(repository)
    ) -> dict[str, Any]:
        document = get_definition(slo_id, request, repo)
        definition = Definition(**{key: document[key] for key in Definition.__dataclass_fields__})
        status = repo.current_status(definition)
        if status is None:
            raise HTTPException(404, detail={"code": "status_not_found", "message": "No evaluation recorded"})
        return status

    @router.get("/reliability/summary")
    def summary(request: Request, repo: ElasticsearchReliabilityRepository = Depends(repository)) -> dict[str, int]:
        return repo.summary(*scope(request))

    @router.get("/reliability/runtime")
    def runtime(request: Request, repo: ElasticsearchReliabilityRepository = Depends(repository)) -> dict[str, Any]:
        tenant, environment = scope(request)
        return {
            "configured": True,
            "worker_id": None,
            "lease_state": "unknown",
            "elasticsearch_dependency_state": "available",
            "definitions_due": len(repo.due(tenant, environment, datetime.now(timezone.utc), 200)),
            "definitions_evaluated": 0,
            "definitions_skipped": 0,
            "latest_successful_evaluation": None,
            "latest_failed_evaluation": None,
            "consecutive_failures": 0,
            "checkpoint_status": "unknown",
        }

    return router
