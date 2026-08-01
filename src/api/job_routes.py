"""Tenant-bound canonical job query API."""

from __future__ import annotations

import base64
import json
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request


def _cursor(value: str | None, tenant: str, environment: str) -> int:
    if not value:
        return 0
    try:
        body = json.loads(base64.urlsafe_b64decode(value + "===").decode())
        if body["tenant"] != tenant or body["environment"] != environment:
            raise ValueError
        return int(body["offset"])
    except Exception as exc:
        raise HTTPException(400, "cursor is invalid for the active tenant and environment") from exc


def _next(offset: int, tenant: str, environment: str) -> str:
    return (
        base64.urlsafe_b64encode(
            json.dumps({"tenant": tenant, "environment": environment, "offset": offset}, separators=(",", ":")).encode()
        )
        .decode()
        .rstrip("=")
    )


def create_job_router(service_dependency: Callable[..., Any], auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"], dependencies=[Depends(auth_dependency)])

    def visible(request: Request, service: Any) -> list[dict[str, Any]]:
        values = getattr(service.store, "_dataobs_jobs", {}).values()
        return [
            x
            for x in values
            if x.get("tenant_id") == request.state.tenant_id and x.get("environment") == request.state.environment
        ]

    @router.get("")
    def jobs(
        request: Request,
        service: Any = Depends(service_dependency),
        search: str | None = None,
        platform: str | None = None,
        owner: str | None = None,
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
    ):
        items = visible(request, service)
        if search:
            items = [x for x in items if search.lower() in (x.get("qualified_name") or "").lower()]
        if platform:
            items = [x for x in items if x.get("platform") == platform]
        if owner:
            items = [x for x in items if x.get("owner") == owner or owner in (x.get("owner") or {}).get("contacts", [])]
        items.sort(key=lambda x: (x.get("last_seen", ""), x["job_id"]), reverse=True)
        offset = _cursor(cursor, request.state.tenant_id, request.state.environment)
        page = items[offset : offset + limit]
        return {
            "items": page,
            "next_cursor": (
                _next(offset + limit, request.state.tenant_id, request.state.environment)
                if offset + limit < len(items)
                else None
            ),
        }

    def one(job_id: str, request: Request, service: Any) -> dict[str, Any]:
        item = service.store.get_dataobs_job(job_id)
        if (
            not item
            or item.get("tenant_id") != request.state.tenant_id
            or item.get("environment") != request.state.environment
        ):
            raise HTTPException(404, "Job not found")
        return item

    @router.get("/{job_id}")
    def job(job_id: str, request: Request, service: Any = Depends(service_dependency)):
        return one(job_id, request, service)

    @router.get("/{job_id}/runs")
    def runs(
        job_id: str, request: Request, service: Any = Depends(service_dependency), limit: int = Query(50, ge=1, le=200)
    ):
        one(job_id, request, service)
        values = getattr(service.store, "_dataobs_job_runs", {}).values()
        return {
            "items": [x for x in values if x.get("job_id") == job_id and x.get("tenant_id") == request.state.tenant_id][
                :limit
            ]
        }

    @router.get("/{job_id}/schedule")
    def schedule(job_id: str, request: Request, service: Any = Depends(service_dependency)):
        return one(job_id, request, service).get("schedule") or {"kind": "unknown", "confidence": 0}

    return router
