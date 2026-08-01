"""Tenant-bound canonical run and runtime-evidence query API."""

from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from services.job_observer.comparison import compare
from services.job_observer.critical_path import calculate

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

    @router.get("/{run_id}/critical-path")
    def critical_path(run_id: str, request: Request, service: Any = Depends(service_dependency)):
        item = one(run_id, request, service)
        tasks = [
            x
            for x in getattr(service.store, "_dataobs_task_runs", {}).values()
            if x.get("run_id") == item["run_id"] and visible(x, request)
        ]
        stages = [
            x
            for x in getattr(service.store, "_dataobs_stage_runs", {}).values()
            if x.get("run_id") == item["run_id"] and visible(x, request)
        ]
        result = calculate((tasks or stages)[:1000])
        result["segments"] = result.pop("segment_details")
        return result

    @router.post("/compare")
    def compare_runs(body: dict[str, Any], request: Request, service: Any = Depends(service_dependency)):
        base = one(str(body.get("base_run_id", "")), request, service)
        target = one(str(body.get("target_run_id", "")), request, service)
        if base.get("environment") != target.get("environment"):
            raise HTTPException(400, "runs must use the same environment")
        warnings = []
        if base.get("job_id") != target.get("job_id"):
            if not body.get("allow_different_jobs"):
                raise HTTPException(400, "runs must normally belong to the same job")
            warnings.append("Runs belong to different jobs")
        result = compare(base, target)
        missing = [
            field
            for field in ("duration_ms", "state", "attempts", "code_version", "deployment_version")
            if base.get(field) is None or target.get(field) is None
        ]
        return {
            "base_run": base,
            "target_run": target,
            **result,
            "changed_entities": [],
            "confidence": max(0.0, 1 - len(missing) / 10),
            "missing_evidence": missing,
            "warnings": warnings,
        }

    def correlated(run_id: str, request: Request, service: Any, attrs: tuple[str, ...]):
        current = one(run_id, request, service)
        items = []
        for attr in attrs:
            for value in getattr(service.store, attr, {}).values():
                if visible(value, request) and (
                    value.get("run_id") == current["run_id"] or value.get("job_id") == current.get("job_id")
                ):
                    relation = "direct" if value.get("run_id") == current["run_id"] else "correlated"
                    items.append({**value, "relationship": relation})
        return {
            "items": items,
            "data_status": "complete" if items else "not_observed",
            "warnings": [],
            "confidence": 1.0 if items else 0.0,
        }

    @router.get("/{run_id}/quality")
    def quality(run_id: str, request: Request, service: Any = Depends(service_dependency)):
        return correlated(run_id, request, service, ("_dataobs_quality_runs", "_dataobs_monitor_evaluations"))

    @router.get("/{run_id}/incidents")
    def incidents(run_id: str, request: Request, service: Any = Depends(service_dependency)):
        return correlated(run_id, request, service, ("_incidents", "_dataobs_incidents"))

    @router.get("/{run_id}/action-eligibility")
    def eligibility(run_id: str, request: Request, service: Any = Depends(service_dependency)):
        current = one(run_id, request, service)
        scopes = set(request.state.principal.get("scopes", []))
        executable = bool({"jobs:execute", "workflows:execute"} & scopes)
        actions = ["request_rerun", "open_source_system", "create_incident", "attach_evidence"]
        if current.get("state") in {"running", "queued"}:
            actions.append("request_cancellation")
        return {
            "run_id": run_id,
            "eligible": executable,
            "actions": actions if executable else [],
            "approval_required": "workflows:approve" not in scopes,
            "reason": None if executable else "permission_denied",
        }

    @router.post("/{run_id}/actions", status_code=202)
    def action(
        run_id: str,
        body: dict[str, Any],
        request: Request,
        service: Any = Depends(service_dependency),
        idempotency_key: str = Header(alias="Idempotency-Key"),
    ):
        current = one(run_id, request, service)
        scopes = set(request.state.principal.get("scopes", []))
        if not ({"jobs:execute", "workflows:execute"} & scopes):
            raise HTTPException(403, "jobs:execute or workflows:execute is required")
        supported = {
            "request_rerun",
            "request_cancellation",
            "open_source_system",
            "create_incident",
            "attach_evidence",
        }
        if body.get("action") not in supported:
            raise HTTPException(400, "action is not supported")
        requests = getattr(service.store, "_dataobs_run_action_requests", None)
        if requests is None:
            requests = service.store._dataobs_run_action_requests = {}
        key = f"{request.state.tenant_id}:{run_id}:{idempotency_key}"
        if key not in requests:
            requests[key] = {
                "request_id": key,
                "tenant_id": request.state.tenant_id,
                "environment": request.state.environment,
                "run_id": current["run_id"],
                "action": body["action"],
                "status": "pending_approval" if "workflows:approve" not in scopes else "accepted",
                "external_execution": False,
            }
        return requests[key]

    return router
