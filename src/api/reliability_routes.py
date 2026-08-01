"""Team 1 stream/pathway reliability HTTP surface."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable

from elasticsearch import ConflictError
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
        tenant = getattr(request.state, "tenant_id", None)
        environment = getattr(request.state, "environment", None)
        if not tenant or not environment:
            raise HTTPException(
                403, detail={"code": "trusted_scope_required", "message": "Authenticated product context is required"}
            )
        return str(tenant), str(environment)

    def actor(request: Request) -> str:
        subject = getattr(getattr(request.state, "principal", None), "subject", None)
        if not subject:
            raise HTTPException(
                403, detail={"code": "mutation_actor_required", "message": "Authenticated actor is required"}
            )
        return str(subject)

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
        mutation_actor = actor(request)
        identifier = hashlib.sha256(
            f"{tenant}\0{environment}\0{mutation_actor}\0{idempotency_key}".encode()
        ).hexdigest()
        document = payload | {
            "id": identifier,
            "tenant_id": tenant,
            "environment": environment,
            "enabled": False,
            "revision": 1,
            "created_at": now,
            "updated_at": now,
            "created_actor": mutation_actor,
            "updated_actor": mutation_actor,
            "schema_version": "v1",
            "next_evaluation_at": now,
        }
        Definition(**{key: document[key] for key in Definition.__dataclass_fields__})
        try:
            repo.es.index(index=DEFINITIONS, id=identifier, document=document, op_type="create", refresh="wait_for")
        except ConflictError:
            existing = repo.es.get(index=DEFINITIONS_READ, id=identifier)["_source"]
            if any(existing.get(key) != value for key, value in payload.items()):
                raise HTTPException(
                    409,
                    detail={"code": "idempotency_conflict", "message": "Idempotency key was used for another request"},
                ) from None
            document = existing
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
        updated["updated_actor"] = actor(request)
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
        health = repo.runtime_health(tenant, environment)
        if health is None:
            return {"configured": False, "state": "not_configured"}
        heartbeat = datetime.fromisoformat(health["heartbeat_at"])
        age = (datetime.now(timezone.utc) - heartbeat.astimezone(timezone.utc)).total_seconds()
        if health.get("elasticsearch_status") == "unavailable":
            state = "elasticsearch_unavailable"
        elif health.get("consecutive_failures", 0) >= 3:
            state = "failed"
        elif health.get("definitions_failed", 0) or health.get("pending_reconciliation_count", 0):
            state = "degraded"
        else:
            state = "stale" if age > 180 else "healthy"
        return health | {"configured": True, "state": state}

    return router
