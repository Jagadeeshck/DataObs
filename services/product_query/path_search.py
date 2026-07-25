"""Deterministic bounded simple-path search with explainable ranking."""

from __future__ import annotations

import hashlib
from collections import defaultdict, deque

from packages.domain_model.investigation import PathwayRoute, PathwayRouteEdge, PathwayRouteNode


def search_paths(
    nodes: list[PathwayRouteNode],
    edges: list[PathwayRouteEdge],
    start: str,
    end: str | None,
    *,
    max_hops: int,
    max_paths: int,
    minimum_confidence: float = 0,
    direction: str = "downstream",
    include_partial: bool = True,
) -> tuple[list[PathwayRoute], list[PathwayRoute], int, bool]:
    """Enumerate bounded loopless paths; ordering is stable for identical evidence."""
    node_by_id = {node.id: node for node in nodes}
    adjacency: dict[str, list[tuple[str, PathwayRouteEdge]]] = defaultdict(list)
    excluded = 0
    for edge in edges:
        if edge.evidence.confidence < minimum_confidence or not edge.evidence.active:
            excluded += 1
            continue
        source, target = edge.source_node_id, edge.destination_node_id
        if direction == "upstream":
            source, target = target, source
        adjacency[source].append((target, edge))
    for value in adjacency.values():
        value.sort(key=lambda item: (item[0], item[1].id))
    queue: deque[tuple[str, list[str], list[PathwayRouteEdge]]] = deque([(start, [start], [])])
    complete: list[PathwayRoute] = []
    partial: list[PathwayRoute] = []
    truncated = False
    while queue:
        current, node_ids, path_edges = queue.popleft()
        if end is not None and current == end:
            complete.append(_route(node_ids, path_edges, node_by_id, True))
            continue
        if len(path_edges) >= max_hops:
            truncated = truncated or bool(adjacency.get(current))
            if include_partial:
                partial.append(_route(node_ids, path_edges, node_by_id, end is None))
            continue
        choices = [(target, edge) for target, edge in adjacency.get(current, []) if target not in node_ids]
        if not choices and include_partial and path_edges:
            partial.append(_route(node_ids, path_edges, node_by_id, end is None))
        for target, edge in choices:
            queue.append((target, node_ids + [target], path_edges + [edge]))
        if len(complete) + len(queue) + len(partial) > 10_000:
            truncated = True
            break
    complete.sort(key=lambda route: (-route.rank_score, route.id))
    partial.sort(key=lambda route: (-route.rank_score, route.id))
    excluded += max(0, len(complete) - max_paths)
    return complete[:max_paths], partial[:max_paths], excluded, truncated or len(complete) > max_paths


def _route(
    node_ids: list[str], edges: list[PathwayRouteEdge], nodes: dict[str, PathwayRouteNode], complete: bool
) -> PathwayRoute:
    confidence = min((edge.evidence.confidence for edge in edges), default=0)
    recency = 1.0 if all(edge.evidence.observed_at for edge in edges) else 0.5
    active = sum(edge.evidence.active for edge in edges) / len(edges) if edges else 0
    completeness = 1.0 if complete else 0.4
    length = 1 / max(1, len(edges))
    factors = {
        "evidence_confidence": confidence,
        "path_completeness": completeness,
        "recency": recency,
        "health": 0.5,
        "path_length": length,
        "business_relevance": 0.0,
        "active_traffic": active,
        "slo_coverage": 0.0,
    }
    score = round(sum(factors.values()) / len(factors), 6)
    route_id = hashlib.sha256("\0".join(node_ids).encode()).hexdigest()[:16]
    return PathwayRoute(
        id=route_id,
        nodes=[nodes[node_id] for node_id in node_ids if node_id in nodes],
        edges=edges,
        complete=complete,
        confidence=confidence,
        rank_score=score,
        ranking_explanation=factors,
    )
