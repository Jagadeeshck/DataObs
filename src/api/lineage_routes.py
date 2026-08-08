"""Bounded lineage API backed exclusively by the Team 2 repository contract."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from services.lineage_intelligence.impact import analyse
from services.lineage_intelligence.models import ImpactRequest, utc_now
from services.lineage_intelligence.traversal import traverse


def create_lineage_router(repository_dependency: Callable[..., Any], auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"], dependencies=[Depends(auth_dependency)])

    def scope(request: Request) -> tuple[str, str]:
        return request.state.tenant_id, request.state.environment

    def graph(
        asset_id: str,
        request: Request,
        repository: Any,
        direction: str,
        depth: int,
        max_nodes: int,
        max_edges: int,
        column: str | None = None,
        include_stale: bool = False,
        as_of: str | None = None,
    ) -> dict:
        if direction not in {"upstream", "downstream", "both"}:
            raise HTTPException(400, "direction must be upstream, downstream, or both")
        tenant, environment = scope(request)
        result = traverse(
            repository,
            tenant,
            environment,
            ImpactRequest(
                asset_id,
                root_column=column,
                direction=direction,
                max_depth=depth,
                max_nodes=max_nodes,
                max_edges=max_edges,
                include_stale_edges=include_stale,
                as_of=as_of,
            ),
        )
        confidences = [float(edge["confidence"]) for edge in result.edges]
        return {
            "request_id": request.state.request_id,
            "root": {"asset_id": asset_id, "column": column},
            "direction": direction,
            "nodes": result.nodes,
            "edges": result.edges,
            "paths": result.paths,
            "cycles": result.cycles,
            "truncated": result.truncated,
            "truncation": {
                "occurred": result.truncated,
                "limits": {"depth": depth, "nodes": max_nodes, "edges": max_edges},
            },
            "data_status": "partial" if result.truncated else "available" if result.edges else "missing",
            "confidence": min(confidences, default=0.0),
            "warnings": result.warnings,
            "evidence_references": sorted({r for e in result.edges for r in e["evidence_refs"]}),
            "observed_at": utc_now(),
        }

    @router.get("/assets/{asset_id}")
    @router.get("/assets/{asset_id}/graph")
    def asset(
        asset_id: str,
        request: Request,
        repository: Any = Depends(repository_dependency),
        direction: str = "both",
        depth: int = Query(3, ge=1, le=10),
        max_nodes: int = Query(200, ge=1, le=1000),
        max_edges: int = Query(500, ge=1, le=2500),
        include_stale: bool = False,
        as_of: str | None = None,
    ):
        return graph(
            asset_id,
            request,
            repository,
            direction,
            depth,
            max_nodes,
            max_edges,
            include_stale=include_stale,
            as_of=as_of,
        )

    @router.get("/assets/{asset_id}/impact")
    def asset_impact(
        asset_id: str,
        request: Request,
        repository: Any = Depends(repository_dependency),
        depth: int = Query(5, ge=1, le=10),
    ):
        return graph(asset_id, request, repository, "downstream", depth, 200, 500)

    @router.get("/assets/{asset_id}/columns/{column}")
    @router.get("/assets/{asset_id}/columns/{column}/impact")
    def column(
        asset_id: str,
        column: str,
        request: Request,
        repository: Any = Depends(repository_dependency),
        direction: str = "both",
        depth: int = Query(3, ge=1, le=10),
    ):
        return graph(asset_id, request, repository, direction, depth, 200, 500, column)

    @router.get("/jobs/{job_id}")
    def job(job_id: str, request: Request, repository: Any = Depends(repository_dependency)):
        tenant, env = scope(request)
        edges = repository.list_edges_by_job(tenant, env, job_id)
        return {
            "request_id": request.state.request_id,
            "job_id": job_id,
            "edges": [asdict(e) for e in edges],
            "data_status": "available" if edges else "missing",
            "confidence": min((e.confidence for e in edges), default=0),
            "warnings": [],
            "truncated": False,
            "observed_at": utc_now(),
            "evidence_references": [],
        }

    @router.get("/runs/{run_id}")
    def run(run_id: str, request: Request, repository: Any = Depends(repository_dependency)):
        tenant, env = scope(request)
        edges = repository.list_edges_by_run(tenant, env, run_id)
        return {
            "request_id": request.state.request_id,
            "run_id": run_id,
            "edges": [asdict(e) for e in edges],
            "data_status": "available" if edges else "missing",
            "confidence": min((e.confidence for e in edges), default=0),
            "warnings": [],
            "truncated": False,
            "observed_at": utc_now(),
            "evidence_references": [],
        }

    @router.get("/changes")
    def changes(
        request: Request, repository: Any = Depends(repository_dependency), limit: int = Query(50, ge=1, le=100)
    ):
        tenant, env = scope(request)
        items = repository.list_schema_changes(tenant, env, limit)
        return {
            "request_id": request.state.request_id,
            "items": items,
            "data_status": "available",
            "confidence": min((float(x.get("confidence", 0)) for x in items), default=0),
            "warnings": [],
            "truncated": len(items) == limit,
            "observed_at": utc_now(),
            "evidence_references": [],
        }

    @router.get("/path")
    def path(
        source_asset_id: str,
        target_asset_id: str,
        request: Request,
        repository: Any = Depends(repository_dependency),
        depth: int = Query(5, ge=1, le=10),
    ):
        result = graph(source_asset_id, request, repository, "downstream", depth, 200, 500)
        result["target_asset_id"] = target_asset_id
        result["paths"] = [path for path in result["paths"] if path[-1] == target_asset_id]
        if not result["paths"]:
            result["warnings"] = [*result["warnings"], "No observed bounded path connects the requested assets"]
        return result

    @router.post("/impact-analyses", status_code=201)
    def create_impact(
        payload: dict,
        request: Request,
        repository: Any = Depends(repository_dependency),
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    ):
        if not idempotency_key or len(idempotency_key) > 128:
            raise HTTPException(400, "a bounded Idempotency-Key is required")
        try:
            analysis_request = ImpactRequest(**payload)
            analysis_request.validate()
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        tenant, env = scope(request)
        existing = repository.get_impact_evaluation(tenant, env, analysis_request.analysis_id(tenant, env))
        return existing or analyse(repository, tenant, env, analysis_request)

    @router.get("/impact-analyses/{analysis_id}")
    def get_impact(analysis_id: str, request: Request, repository: Any = Depends(repository_dependency)):
        tenant, env = scope(request)
        result = repository.get_impact_evaluation(tenant, env, analysis_id)
        if result is None:
            raise HTTPException(404, "impact analysis not found")
        return result

    return router
