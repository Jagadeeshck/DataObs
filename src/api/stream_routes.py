from __future__ import annotations

import os
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from services.product_query.stream_common import envelope
from services.product_query.stream_pagination import CursorCodec, CursorState, InvalidCursor
from services.product_query.stream_repository import StreamRepository


class CompareRequest(BaseModel):
    mode: str = Field(
        pattern="^(previous_window|selected_window|rolling_baseline|same_period_previous_day|same_period_previous_week|before_after_change)$"
    )
    start: str | None = None
    end: str | None = None


class ActionRequest(BaseModel):
    action: str = Field(pattern="^(restart_failed_connector|restart_failed_task|verify_recovery)$")
    reason: str = Field(min_length=8, max_length=500)


def create_stream_router(get_es: Callable[..., Any], require_auth: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["stream-360"], dependencies=[Depends(require_auth)])
    secret = os.getenv("DATAOBS_CURSOR_SECRET", "development-cursor-secret-change-me")
    codec = CursorCodec(secret)

    def repo(es: Any = Depends(get_es)) -> StreamRepository:
        return StreamRepository(es.es)

    def context(request: Request, environment: str) -> tuple[str, str]:
        return request.state.tenant_id, environment

    async def listing(
        resource: str, request: Request, environment: str, limit: int, cursor: str | None, repository: StreamRepository
    ) -> dict[str, Any]:
        tenant, environment = context(request, environment)
        filters = {"resource": resource, "limit": limit}
        after = None
        if cursor:
            try:
                after = codec.decode(cursor, tenant=tenant, environment=environment, filters=filters).sort
            except InvalidCursor as exc:
                raise HTTPException(400, detail={"code": "invalid_cursor", "message": str(exc)}) from exc
        rows = repository.search(resource, tenant, environment, size=limit + 1, search_after=after)
        page, extra = rows[:limit], len(rows) > limit
        next_cursor = (
            codec.encode(CursorState(page[-1].pop("_sort")), tenant=tenant, environment=environment, filters=filters)
            if page and extra
            else None
        )
        for item in page:
            item.pop("_sort", None)
        return {
            "items": page,
            "next_cursor": next_cursor,
            **envelope(request.state.request_id, configured=True, found=bool(page), sources=["kafka_observer"]),
        }

    @router.get("/streams")
    async def streams(
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        repository: StreamRepository = Depends(repo),
    ) -> dict[str, Any]:
        return await listing("streams", request, environment, limit, cursor, repository)

    @router.get("/stream-clusters")
    async def clusters(
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        repository: StreamRepository = Depends(repo),
    ) -> dict[str, Any]:
        return await listing("clusters", request, environment, limit, cursor, repository)

    @router.get("/consumer-groups")
    async def groups(
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        repository: StreamRepository = Depends(repo),
    ) -> dict[str, Any]:
        return await listing("consumer_groups", request, environment, limit, cursor, repository)

    @router.get("/stream-connectors")
    async def connectors(
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        repository: StreamRepository = Depends(repo),
    ) -> dict[str, Any]:
        return await listing("connectors", request, environment, limit, cursor, repository)

    @router.get("/schema-subjects")
    async def schemas(
        request: Request,
        environment: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        repository: StreamRepository = Depends(repo),
    ) -> dict[str, Any]:
        return await listing("schemas", request, environment, limit, cursor, repository)

    detail_roots = {
        "streams": "streams",
        "stream-clusters": "clusters",
        "consumer-groups": "consumer_groups",
        "stream-connectors": "connectors",
        "schema-subjects": "schemas",
    }

    async def detail(
        root: str, resource_id: str, request: Request, environment: str, repository: StreamRepository
    ) -> dict[str, Any]:
        tenant, environment = context(request, environment)
        document = repository.get(detail_roots[root], resource_id, tenant, environment)
        if document is None:
            raise HTTPException(404, detail="Stream resource not found")
        return {
            "item": document,
            **envelope(request.state.request_id, configured=True, found=True, sources=["kafka_observer"]),
        }

    for root in detail_roots:

        async def handler(
            resource_id: str,
            request: Request,
            environment: str = Query(...),
            repository: StreamRepository = Depends(repo),
            _root: str = root,
        ) -> dict[str, Any]:
            return await detail(_root, resource_id, request, environment, repository)

        router.add_api_route(f"/{root}/{{resource_id}}", handler, methods=["GET"], name=f"get_{root}")

    @router.get("/streams/{resource_id}/inspection-policy")
    async def inspection_policy(resource_id: str, request: Request) -> dict[str, Any]:
        return {
            "stream_id": resource_id,
            "enabled": False,
            "reason": "Message inspection is disabled by default",
            **envelope(request.state.request_id, configured=False, found=False),
        }

    @router.post("/streams/{resource_id}/inspect", status_code=403)
    async def inspect(resource_id: str) -> None:
        raise HTTPException(403, detail={"code": "inspection_disabled", "message": "Message inspection is disabled"})

    @router.post("/stream-connectors/{resource_id}/actions", status_code=202)
    async def connector_action(
        resource_id: str, body: ActionRequest, idempotency_key: str | None = Header(None, alias="Idempotency-Key")
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise HTTPException(400, detail={"code": "idempotency_required", "message": "Idempotency-Key is required"})
        return {
            "connector_id": resource_id,
            "action": body.action,
            "state": "awaiting_approval",
            "idempotency_key": idempotency_key,
        }

    for root in ("streams", "stream-clusters", "consumer-groups"):

        async def compare(
            resource_id: str, body: CompareRequest, request: Request, _root: str = root
        ) -> dict[str, Any]:
            return {
                "resource_type": _root,
                "resource_id": resource_id,
                "mode": body.mode,
                "deltas": [],
                "sample_count": 0,
                **envelope(request.state.request_id, configured=True, found=False),
            }

        router.add_api_route(f"/{root}/{{resource_id}}/compare", compare, methods=["POST"], name=f"compare_{root}")
    return router
