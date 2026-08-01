"""Tenant-bound canonical run and runtime-evidence query API."""

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request

COLLECTIONS = {
    "events": "_dataobs_lineage_events",
    "attempts": "_dataobs_attempts",
    "tasks": "_dataobs_task_runs",
    "stages": "_dataobs_stage_runs",
    "streaming-queries": "_dataobs_streaming_queries",
}


def create_run_router(service_dependency: Callable[..., Any], auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/runs", tags=["runs"], dependencies=[Depends(auth_dependency)])

    def visible(item, request):
        return item.get("tenant_id") == request.state.tenant_id and item.get("environment") == request.state.environment

    def one(run_id, request, service):
        item = service.get_job_run(run_id)
        if not item or not visible(item, request):
            raise HTTPException(404, "Run not found")
        return item

    @router.get("")
    def runs(
        request: Request,
        service: Any = Depends(service_dependency),
        job_id: str | None = None,
        state: str | None = None,
        platform: str | None = None,
        asset_id: str | None = None,
        failure_category: str | None = None,
        started_after: str | None = None,
        started_before: str | None = None,
        has_quality_failure: bool | None = None,
        has_incident: bool | None = None,
        limit: int = Query(50, ge=1, le=200),
    ):
        items = [x for x in getattr(service.store, "_dataobs_job_runs", {}).values() if visible(x, request)]
        filters = {"job_id": job_id, "state": state, "platform": platform}
        for key, value in filters.items():
            if value is not None:
                items = [x for x in items if x.get(key) == value]
        if asset_id:
            items = [x for x in items if asset_id in x.get("input_assets", []) + x.get("output_assets", [])]
        if failure_category:
            items = [x for x in items if (x.get("failure") or {}).get("category") == failure_category]
        if started_after:
            items = [x for x in items if (x.get("started_at") or "") >= started_after]
        if started_before:
            items = [x for x in items if (x.get("started_at") or "") <= started_before]
        if has_quality_failure is not None:
            items = [x for x in items if bool(x.get("has_quality_failure")) == has_quality_failure]
        if has_incident is not None:
            items = [x for x in items if bool(x.get("has_incident")) == has_incident]
        return {"items": sorted(items, key=lambda x: x.get("started_at") or "", reverse=True)[:limit]}

    @router.get("/{run_id}")
    def run(run_id: str, request: Request, service: Any = Depends(service_dependency)):
        return one(run_id, request, service)

    for suffix, attr in COLLECTIONS.items():

        def endpoint(run_id: str, request: Request, service: Any = Depends(service_dependency), _attr=attr):
            current = one(run_id, request, service)
            values = getattr(service.store, _attr, {}).values()
            return {"items": [x for x in values if x.get("run_id") == current["run_id"] and visible(x, request)]}

        router.add_api_route(f"/{{run_id}}/{suffix}", endpoint, methods=["GET"], name=f"run_{suffix}")

    @router.get("/{run_id}/datasets")
    def datasets(run_id: str, request: Request, service: Any = Depends(service_dependency)):
        item = one(run_id, request, service)
        return {"inputs": item.get("input_assets", []), "outputs": item.get("output_assets", [])}

    return router
