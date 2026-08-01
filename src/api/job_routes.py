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

    def related(job_id: str, request: Request, service: Any, attrs: tuple[str, ...]):
        one(job_id, request, service)
        items = []
        for attr in attrs:
            for value in getattr(service.store, attr, {}).values():
                if (
                    value.get("tenant_id") == request.state.tenant_id
                    and value.get("environment") == request.state.environment
                    and value.get("job_id") == job_id
                ):
                    items.append({**value, "relationship": "direct"})
        return {
            "items": items,
            "data_status": "complete" if items else "not_observed",
            "confidence": 1.0 if items else 0.0,
            "warnings": [],
        }

    @router.get("/{job_id}/quality")
    def quality(job_id: str, request: Request, service: Any = Depends(service_dependency)):
        return related(job_id, request, service, ("_dataobs_quality_runs", "_dataobs_monitor_evaluations"))

    @router.get("/{job_id}/incidents")
    def incidents(job_id: str, request: Request, service: Any = Depends(service_dependency)):
        return related(job_id, request, service, ("_incidents", "_dataobs_incidents"))

    @router.get("/{job_id}/slo")
    def slo(job_id: str, request: Request, service: Any = Depends(service_dependency)):
        item = one(job_id, request, service)
        return item.get("slo") or {
            "job_id": job_id,
            "data_status": "not_configured",
            "warnings": ["No duration SLO is configured"],
        }

    @router.get("/{job_id}/reliability")
    def reliability(job_id: str, request: Request, service: Any = Depends(service_dependency)):
        item = one(job_id, request, service)
        runs = [
            x
            for x in getattr(service.store, "_dataobs_job_runs", {}).values()
            if x.get("tenant_id") == request.state.tenant_id
            and x.get("environment") == request.state.environment
            and x.get("job_id") == job_id
        ]
        components: dict[str, float | None] = {
            "success_rate": None,
            "schedule_adherence": None,
            "duration_slo": None,
            "missing_run_rate": None,
            "retry_rate": None,
            "quality_failure_rate": None,
            "dependency_failure_rate": None,
        }
        if runs:
            components["success_rate"] = sum(x.get("state") == "success" for x in runs) / len(runs)
            components["retry_rate"] = 1 - sum(bool(x.get("attempts", 1) > 1) for x in runs) / len(runs)
            components["quality_failure_rate"] = 1 - sum(bool(x.get("has_quality_failure")) for x in runs) / len(runs)
        schedule = item.get("schedule") or {}
        if schedule.get("kind") not in {"ad_hoc", "unknown", None} and schedule.get("confidence", 0) >= 0.8:
            components["schedule_adherence"] = item.get("schedule_adherence")
            components["missing_run_rate"] = item.get("missing_run_rate")
        available = {k: v for k, v in components.items() if v is not None}
        weights = {k: 1 / len(available) for k in available} if available else {}
        score = sum(float(available[k]) * weights[k] for k in available) * 100 if len(available) >= 2 else None
        return {
            "score": score,
            "components": components,
            "weights": weights,
            "formula": "100 * weighted_mean(available normalized components)",
            "confidence": min(1.0, len(available) / len(components)),
            "missing_components": [k for k, v in components.items() if v is None],
            "observed_period": {"run_count": len(runs)},
            "missing_run": item.get("missing_run")
            or {"state": "unknown", "reason": "schedule evidence is insufficient"},
        }

    return router
