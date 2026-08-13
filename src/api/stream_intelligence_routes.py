"""Authenticated, persisted Stream Intelligence API."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response

from packages.streaming.intelligence import CAPABILITIES, METHODS, DetectorDefinition
from services.kafka_observer.intelligence_repository import ElasticsearchIntelligenceRepository
from services.kafka_observer.reliability_runtime import StaleWriter
from services.product_query.stream_pagination import CursorCodec, CursorState, InvalidCursor


def create_stream_intelligence_router(get_es: Callable[..., Any], require_auth: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["stream-intelligence"], dependencies=[Depends(require_auth)])
    codec = CursorCodec(os.getenv("DATAOBS_CURSOR_SECRET", "development-cursor-secret-change-me"))

    def repository(es: Any = Depends(get_es)) -> ElasticsearchIntelligenceRepository:
        return ElasticsearchIntelligenceRepository(es.es)

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
                403, detail={"code": "trusted_actor_required", "message": "Authenticated actor is required"}
            )
        return str(subject)

    @router.get("/stream-intelligence/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "resource_types": [
                {"resource_type": kind, "metrics": sorted(metrics)} for kind, metrics in CAPABILITIES.items()
            ],
            "detector_methods": sorted(METHODS),
            "directions": ["high", "low", "both"],
            "required_minimum_samples": 3,
            "seasonal_support": ["hour_of_day", "day_of_week_hour"],
            "elastic_ml_required": False,
            "unavailable_capabilities": [
                {"metric": "message_payload_analysis", "reason": "raw payload access is prohibited"}
            ],
        }

    def page(
        kind: str,
        request: Request,
        repo: ElasticsearchIntelligenceRepository,
        limit: int,
        cursor: str | None,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        tenant, environment = scope(request)
        context = filters | {"page_size": limit}
        try:
            after = (
                codec.decode(
                    cursor,
                    tenant=tenant,
                    environment=environment,
                    filters=context,
                    route=kind,
                    sort={"evaluated_at": "desc"},
                ).sort
                if cursor
                else None
            )
        except InvalidCursor as exc:
            raise HTTPException(400, detail={"code": "invalid_cursor", "message": str(exc)}) from exc
        result = repo.inventory(kind, tenant, environment, size=limit, filters=filters, after=after)
        next_cursor = (
            codec.encode(
                CursorState(result["last_sort"]),
                tenant=tenant,
                environment=environment,
                filters=context,
                route=kind,
                sort={"evaluated_at": "desc"},
            )
            if result["last_sort"] and len(result["items"]) == limit
            else None
        )
        return {"items": result["items"], "next_cursor": next_cursor}

    @router.get("/stream-intelligence/summary")
    def summary(request: Request, repo: ElasticsearchIntelligenceRepository = Depends(repository)) -> dict[str, Any]:
        tenant, environment = scope(request)
        return {"counts": repo.summary_counts(tenant, environment), "data_status": "persisted"}

    @router.get("/stream-intelligence/runtime")
    def runtime(request: Request, repo: ElasticsearchIntelligenceRepository = Depends(repository)) -> dict[str, Any]:
        tenant, environment = scope(request)
        health = repo.runtime_health(tenant, environment)
        return health or {"configured": False, "health_state": "not_configured", "data_status": "unknown"}

    @router.get("/streams/{resource_id}/capacity")
    def stream_capacity(
        resource_id: str,
        request: Request,
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        """Return raw capacity intelligence in trusted request scope."""
        tenant, environment = scope(request)
        try:
            return repo.get_capacity(tenant, environment, resource_id)
        except KeyError:
            raise HTTPException(404, detail={"code": "capacity_not_found", "message": "Capacity evaluation not found"}) from None

    @router.get("/stream-intelligence/capacity")
    def capacity_inventory(
        request: Request,
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        provider: str | None = None,
        messaging_system: str | None = None,
        state: str | None = None,
        bottleneck_dimension: str | None = None,
        throttled: bool | None = None,
        retention_risk: bool | None = None,
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        return page("capacity", request, repo, limit, cursor, {"provider": provider, "messaging_system": messaging_system, "overall_state": state, "bottleneck_dimension": bottleneck_dimension, "throttled": throttled, "retention_risk": retention_risk})

    for route_kind in ("anomalies", "forecasts", "failure-candidates", "signals"):

        def inventory(
            request: Request,
            limit: int = Query(50, ge=1, le=200),
            cursor: str | None = None,
            resource_type: str | None = None,
            resource_id: str | None = None,
            state: str | None = None,
            repo: ElasticsearchIntelligenceRepository = Depends(repository),
            _kind: str = route_kind,
        ) -> dict[str, Any]:
            return page(
                _kind,
                request,
                repo,
                limit,
                cursor,
                {"resource_type": resource_type, "resource_id": resource_id, "state": state},
            )

        router.add_api_route(
            f"/stream-intelligence/{route_kind}",
            inventory,
            methods=["GET"],
            name=f"list-stream-intelligence-{route_kind}",
        )

    @router.get("/stream-detectors")
    def list_detectors(
        request: Request,
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        enabled: bool | None = None,
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        tenant, environment = scope(request)
        filters = {"resource_type": resource_type, "resource_id": resource_id, "enabled": enabled, "page_size": limit}
        try:
            after = (
                codec.decode(
                    cursor,
                    tenant=tenant,
                    environment=environment,
                    filters=filters,
                    route="detectors",
                    sort={"updated_at": "desc"},
                ).sort
                if cursor
                else None
            )
        except InvalidCursor as exc:
            raise HTTPException(400, detail={"code": "invalid_cursor", "message": str(exc)}) from exc
        result = repo.list_detectors(tenant, environment, size=limit, filters=filters, after=after)
        next_cursor = (
            codec.encode(
                CursorState(result["last_sort"]),
                tenant=tenant,
                environment=environment,
                filters=filters,
                route="detectors",
                sort={"updated_at": "desc"},
            )
            if result["last_sort"] and len(result["items"]) == limit
            else None
        )
        return {"items": result["items"], "next_cursor": next_cursor}

    @router.post("/stream-detectors", status_code=201)
    def create_detector(
        payload: dict[str, Any],
        request: Request,
        response: Response,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        tenant, environment, mutation_actor = *scope(request), actor(request)
        now = datetime.now(timezone.utc)
        detector_id = hashlib.sha256(
            f"{tenant}\0{environment}\0{mutation_actor}\0{idempotency_key}".encode()
        ).hexdigest()
        document = payload | {
            "detector_id": detector_id,
            "tenant_id": tenant,
            "environment": environment,
            "enabled": False,
            "revision": 1,
            "created_actor": mutation_actor,
            "updated_actor": mutation_actor,
            "created_at": now,
            "updated_at": now,
            "next_evaluation_at": now,
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        try:
            created = repo.create_detector(DetectorDefinition(**document), fingerprint)
        except ValueError as exc:
            code = "idempotency_conflict" if "fingerprint" in str(exc) else "invalid_detector"
            raise HTTPException(
                409 if code == "idempotency_conflict" else 422, detail={"code": code, "message": str(exc)}
            ) from exc
        response.headers["ETag"] = f'"{created["revision"]}"'
        return {key: value for key, value in created.items() if not key.startswith("_")}

    def get_scoped(detector_id: str, request: Request, repo: ElasticsearchIntelligenceRepository) -> dict[str, Any]:
        try:
            return repo.get_detector(*scope(request), detector_id)
        except KeyError as exc:
            raise HTTPException(404, detail={"code": "not_found", "message": "Detector not found"}) from exc

    @router.get("/stream-detectors/{detector_id}")
    def get_detector(
        detector_id: str,
        request: Request,
        response: Response,
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        item = get_scoped(detector_id, request, repo)
        response.headers["ETag"] = f'"{item["revision"]}"'
        return {key: value for key, value in item.items() if not key.startswith("_")}

    def revision_of(if_match: str | None) -> int:
        if not if_match:
            raise HTTPException(428, detail={"code": "precondition_required", "message": "If-Match is required"})
        try:
            return int(if_match.strip('"'))
        except ValueError as exc:
            raise HTTPException(400, detail={"code": "invalid_etag", "message": "If-Match is invalid"}) from exc

    def mutate(
        detector_id: str,
        payload: dict[str, Any],
        request: Request,
        response: Response,
        if_match: str | None,
        repo: ElasticsearchIntelligenceRepository,
    ) -> dict[str, Any]:
        tenant, environment = scope(request)
        try:
            item = repo.update_detector(
                tenant, environment, detector_id, payload, revision=revision_of(if_match), actor=actor(request)
            )
        except KeyError as exc:
            raise HTTPException(404, detail={"code": "not_found", "message": "Detector not found"}) from exc
        except StaleWriter as exc:
            raise HTTPException(412, detail={"code": "stale_revision", "message": str(exc)}) from exc
        response.headers["ETag"] = f'"{item["revision"]}"'
        return {key: value for key, value in item.items() if not key.startswith("_")}

    @router.patch("/stream-detectors/{detector_id}")
    def patch_detector(
        detector_id: str,
        payload: dict[str, Any],
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match"),
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        return mutate(detector_id, payload, request, response, if_match, repo)

    @router.post("/stream-detectors/{detector_id}/enable")
    def enable_detector(
        detector_id: str,
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match"),
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        return mutate(detector_id, {"enabled": True}, request, response, if_match, repo)

    @router.post("/stream-detectors/{detector_id}/disable")
    def disable_detector(
        detector_id: str,
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match"),
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        return mutate(detector_id, {"enabled": False}, request, response, if_match, repo)

    @router.delete("/stream-detectors/{detector_id}", status_code=204)
    def delete_detector(
        detector_id: str,
        request: Request,
        if_match: str | None = Header(None, alias="If-Match"),
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> Response:
        tenant, environment = scope(request)
        try:
            repo.delete_detector(tenant, environment, detector_id, revision=revision_of(if_match))
        except KeyError as exc:
            raise HTTPException(404, detail={"code": "not_found", "message": "Detector not found"}) from exc
        except StaleWriter as exc:
            raise HTTPException(412, detail={"code": "stale_revision", "message": str(exc)}) from exc
        return Response(status_code=204)

    @router.get("/stream-detectors/{detector_id}/status")
    def detector_status(
        detector_id: str, request: Request, repo: ElasticsearchIntelligenceRepository = Depends(repository)
    ) -> dict[str, Any]:
        definition = get_scoped(detector_id, request, repo)
        results = repo.inventory(
            "anomalies", *scope(request), size=1, filters={"detector_id": definition["detector_id"]}
        )
        return (
            results["items"][0]
            if results["items"]
            else {
                "detector_id": detector_id,
                "state": "disabled" if not definition["enabled"] else "insufficient_data",
                "data_status": "not_evaluated",
            }
        )

    @router.get("/stream-detectors/{detector_id}/evaluations")
    def detector_evaluations(
        detector_id: str,
        request: Request,
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        repo: ElasticsearchIntelligenceRepository = Depends(repository),
    ) -> dict[str, Any]:
        get_scoped(detector_id, request, repo)
        return page("evaluations", request, repo, limit, cursor, {"detector_id": detector_id})

    return router
