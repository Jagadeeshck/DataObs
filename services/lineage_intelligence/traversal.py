from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass

from .models import ImpactRequest, LineageEdge
from .repository import LineageRepository


@dataclass(frozen=True)
class TraversalResult:
    nodes: tuple[dict, ...]
    edges: tuple[dict, ...]
    paths: tuple[tuple[str, ...], ...]
    cycles: tuple[tuple[str, str], ...]
    truncated: bool
    warnings: tuple[str, ...]


def traverse(
    repository: LineageRepository, tenant_id: str, environment: str, request: ImpactRequest
) -> TraversalResult:
    request.validate()
    queue: deque[tuple[str, int, tuple[str, ...]]] = deque([(request.root_asset_id, 0, (request.root_asset_id,))])
    visited = {request.root_asset_id}
    nodes = [{"id": request.root_asset_id, "asset_id": request.root_asset_id, "depth": 0}]
    edges: dict[str, LineageEdge] = {}
    paths: list[tuple[str, ...]] = []
    cycles: set[tuple[str, str]] = set()
    truncated = False
    while queue and not truncated:
        current, depth, path = queue.popleft()
        if depth >= request.max_depth:
            continue
        adjacent = repository.list_adjacent_edges(
            tenant_id,
            environment,
            (current,),
            request.direction,
            column=request.root_column is not None,
            include_stale=request.include_stale_edges,
            as_of=request.as_of,
            limit=min(request.max_edges - len(edges) + 1, 500),
        )
        for edge in adjacent:
            if len(edges) >= request.max_edges:
                truncated = True
                break
            edges.setdefault(edge.edge_id, edge)
            candidates: list[str] = []
            if request.direction in {"downstream", "both"} and edge.source_asset_id == current:
                candidates.append(edge.target_asset_id)
            if request.direction in {"upstream", "both"} and edge.target_asset_id == current:
                candidates.append(edge.source_asset_id)
            for target in candidates:
                if target in path:
                    cycles.add((current, target))
                    continue
                target_path = (*path, target)
                if len(paths) < request.max_paths:
                    paths.append(target_path)
                elif target not in visited:
                    truncated = True
                if target not in visited:
                    if len(nodes) >= request.max_nodes:
                        truncated = True
                        break
                    visited.add(target)
                    nodes.append({"id": target, "asset_id": target, "depth": depth + 1})
                    queue.append((target, depth + 1, target_path))
    warnings = ("bounded graph is partial; do not interpret it as a complete blast radius",) if truncated else ()
    return TraversalResult(
        tuple(nodes),
        tuple(asdict(e) for e in sorted(edges.values(), key=lambda x: x.edge_id)),
        tuple(paths),
        tuple(sorted(cycles)),
        truncated,
        warnings,
    )
