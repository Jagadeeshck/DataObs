"""Canonical, bounded lineage investigation API.

The OpenLineage writer remains the sole owner of lineage projection writes.  This
module deliberately only reads those projections and applies the request's
tenant/environment boundary before graph construction.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _response(
    root: dict[str, Any],
    direction: str,
    depth: int,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    truncated: bool,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    evidence = sorted({ref for edge in edges for ref in edge.get("evidence_refs", [])})
    confidences = [float(edge.get("confidence", 0)) for edge in edges]
    actual = max((int(node.get("depth", 0)) for node in nodes), default=0)
    return {
        "root": root,
        "direction": direction,
        "requested_depth": depth,
        "actual_depth": actual,
        "nodes": nodes,
        "edges": edges,
        "truncated": truncated,
        "data_status": "complete" if edges else "not_observed",
        "source_coverage": ["openlineage"] if edges else [],
        "confidence": min(confidences) if confidences else 0.0,
        "warnings": [*(warnings or []), *(["Graph was truncated at a configured safety limit"] if truncated else [])],
        "evidence_refs": evidence,
        "observed_at": max((e.get("observed_at", "") for e in edges), default=_now()),
    }


def create_lineage_router(service_dependency: Callable[..., Any], auth_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"], dependencies=[Depends(auth_dependency)])

    def scoped(request: Request, service: Any, column: bool = False) -> list[dict[str, Any]]:
        attr = "_dataobs_column_lineage_edges" if column else "_dataobs_lineage_edges"
        return [
            dict(edge)
            for edge in getattr(service.store, attr, {}).values()
            if edge.get("tenant_id") == request.state.tenant_id
            and edge.get("environment") == request.state.environment
            and edge.get("active", True)
        ]

    def graph(
        asset_id: str,
        request: Request,
        service: Any,
        direction: str,
        depth: int,
        max_nodes: int,
        max_edges: int,
        column: str | None = None,
    ) -> dict[str, Any]:
        if direction not in {"upstream", "downstream", "both"}:
            raise HTTPException(400, "direction must be upstream, downstream, or both")
        all_edges = scoped(request, service, column is not None)
        queue = deque([(asset_id, column, 0)])
        visited = {(asset_id, column)}
        nodes = [{"id": asset_id, "asset_id": asset_id, "column": column, "depth": 0}]
        found: list[dict[str, Any]] = []
        truncated = False
        while queue:
            current_asset, current_column, level = queue.popleft()
            if level >= depth:
                continue
            candidates = []
            for edge in all_edges:
                upstream = edge.get("target_asset_id") == current_asset and (
                    column is None or edge.get("target_column") == current_column
                )
                downstream = edge.get("source_asset_id") == current_asset and (
                    column is None or edge.get("source_column") == current_column
                )
                if (direction in {"upstream", "both"} and upstream) or (
                    direction in {"downstream", "both"} and downstream
                ):
                    candidates.append((edge, upstream))
            for edge, upstream in candidates:
                if len(found) >= max_edges:
                    truncated = True
                    break
                if edge["edge_id"] not in {item["edge_id"] for item in found}:
                    found.append(edge)
                adjacent = (
                    (edge["source_asset_id"], edge.get("source_column"))
                    if upstream
                    else (edge["target_asset_id"], edge.get("target_column"))
                )
                if adjacent not in visited:
                    if len(nodes) >= max_nodes:
                        truncated = True
                        continue
                    visited.add(adjacent)
                    nodes.append(
                        {
                            "id": f"{adjacent[0]}#{adjacent[1]}" if adjacent[1] else adjacent[0],
                            "asset_id": adjacent[0],
                            "column": adjacent[1],
                            "depth": level + 1,
                        }
                    )
                    queue.append((*adjacent, level + 1))
        return _response(
            {"asset_id": asset_id, **({"column": column} if column else {})}, direction, depth, nodes, found, truncated
        )

    @router.get("/assets/{asset_id}")
    def asset(
        asset_id: str,
        request: Request,
        service: Any = Depends(service_dependency),
        direction: str = "both",
        depth: int = Query(3, ge=1, le=10),
        max_nodes: int = Query(200, ge=1, le=1000),
        max_edges: int = Query(500, ge=1, le=2500),
    ):
        return graph(asset_id, request, service, direction, depth, max_nodes, max_edges)

    @router.get("/assets/{asset_id}/impact")
    def impact(
        asset_id: str,
        request: Request,
        service: Any = Depends(service_dependency),
        depth: int = Query(5, ge=1, le=10),
        max_nodes: int = Query(200, ge=1, le=1000),
        max_edges: int = Query(500, ge=1, le=2500),
    ):
        return graph(asset_id, request, service, "downstream", depth, max_nodes, max_edges)

    @router.get("/assets/{asset_id}/columns/{column}")
    def columns(
        asset_id: str,
        column: str,
        request: Request,
        service: Any = Depends(service_dependency),
        direction: str = "both",
        depth: int = Query(3, ge=1, le=10),
        max_nodes: int = Query(200, ge=1, le=1000),
        max_edges: int = Query(500, ge=1, le=2500),
    ):
        return graph(asset_id, request, service, direction, depth, max_nodes, max_edges, column)

    def overlay(key: str, value: str, request: Request, service: Any) -> dict[str, Any]:
        edges = [
            edge for edge in scoped(request, service) if edge.get(key) == value or edge.get(f"{key}_run_id") == value
        ]
        assets = sorted({x for edge in edges for x in (edge["source_asset_id"], edge["target_asset_id"])})
        return _response({key: value}, "both", 1, [{"id": x, "asset_id": x, "depth": 1} for x in assets], edges, False)

    @router.get("/jobs/{job_id}")
    def job(job_id: str, request: Request, service: Any = Depends(service_dependency)):
        return overlay("job_id", job_id, request, service)

    @router.get("/runs/{run_id}")
    def run(run_id: str, request: Request, service: Any = Depends(service_dependency)):
        return overlay("run_id", run_id, request, service)

    @router.get("/path")
    def path(
        source_asset_id: str,
        target_asset_id: str,
        request: Request,
        service: Any = Depends(service_dependency),
        depth: int = Query(5, ge=1, le=10),
    ):
        result = graph(source_asset_id, request, service, "downstream", depth, 200, 500)
        if target_asset_id not in {node["asset_id"] for node in result["nodes"]}:
            result["warnings"].append("No observed path connects the requested assets")
            result["data_status"] = "not_observed"
        result["root"]["target_asset_id"] = target_asset_id
        return result

    return router
