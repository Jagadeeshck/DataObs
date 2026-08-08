"""Deterministic, iterative and bounded pathway traversal."""

from __future__ import annotations

from collections import deque

from .investigation import (
    BlastRadiusResult,
    HistoricalEdge,
    HistoricalNode,
    ImpactCandidate,
    TraversalPath,
    TraversalRequest,
)


def traverse(nodes: list[HistoricalNode], edges: list[HistoricalEdge], request: TraversalRequest) -> BlastRadiusResult:
    node_map = {node.node_id: node for node in sorted(nodes, key=lambda n: n.node_id)}
    anchor = request.anchor.anchor_id
    if anchor not in node_map:
        return BlastRadiusResult(request.anchor, request.direction, (), (), False, None, 0, 0)
    unique_edges = {edge.edge_id: edge for edge in edges}
    ordered = sorted(
        unique_edges.values(), key=lambda e: (e.source_node_id, e.destination_node_id, e.relationship, e.edge_id)
    )
    adjacent: dict[str, list[tuple[HistoricalEdge, str, str]]] = {}
    for edge in ordered:
        if request.direction in {"downstream", "both"}:
            adjacent.setdefault(edge.source_node_id, []).append((edge, edge.destination_node_id, "downstream"))
        if request.direction in {"upstream", "both"}:
            adjacent.setdefault(edge.destination_node_id, []).append((edge, edge.source_node_id, "upstream"))
    queue: deque[tuple[str, int, tuple[str, ...], float, frozenset[str], frozenset[str], str, str]] = deque(
        [(anchor, 0, (anchor,), 1.0, frozenset(), frozenset(), "complete", "anchor")]
    )
    visited = {anchor}
    paths: list[TraversalPath] = []
    used_edges: set[str] = set()
    reasons: set[str] = set()
    while queue:
        current, distance, path, confidence, coverage, refs, status, relationship = queue.popleft()
        paths.append(
            TraversalPath(
                current,
                distance,
                relationship,
                path,
                round(confidence, 3),
                tuple(sorted(coverage)),
                tuple(sorted(refs)),
                status,
            )
        )
        if len(paths) >= request.max_paths:
            if queue or adjacent.get(current):
                reasons.add("max_paths")
            break
        neighbours = sorted(adjacent.get(current, []), key=lambda item: (item[1], item[0].edge_id, item[2]))
        if distance >= request.max_hops:
            if neighbours:
                reasons.add("max_hops")
            continue
        for edge, target, relation in neighbours:
            if edge.edge_id not in used_edges and len(used_edges) >= request.max_edges:
                reasons.add("max_edges")
                continue
            used_edges.add(edge.edge_id)
            if target in visited:
                continue
            if len(visited) >= request.max_nodes:
                reasons.add("max_nodes")
                continue
            visited.add(target)
            node = node_map.get(target, HistoricalNode(target, "unknown", data_status="partial", confidence=0.0))
            next_status = (
                "stale"
                if "stale" in {status, edge.data_status, node.data_status}
                else ("partial" if "partial" in {status, edge.data_status, node.data_status} else "complete")
            )
            queue.append(
                (
                    target,
                    distance + 1,
                    path + (target,),
                    min(confidence, edge.confidence, node.confidence),
                    coverage | frozenset(edge.source_coverage) | frozenset(node.source_coverage),
                    refs | frozenset(edge.evidence_refs) | frozenset(node.evidence_refs),
                    next_status,
                    relation,
                )
            )
    candidates = tuple(
        ImpactCandidate(
            node_map.get(p.entity_id, HistoricalNode(p.entity_id, "unknown")).node_type,
            p.entity_id,
            node_map.get(p.entity_id, HistoricalNode(p.entity_id, "unknown")).display_name or p.entity_id,
            p.distance,
            p.relationship,
            p.path,
            "direct" if p.distance <= 1 else "transitive",
            p.confidence,
            p.source_coverage,
            p.evidence_refs,
            (),
            p.data_status,
        )
        for p in paths
    )
    excluded_nodes = max(0, len(node_map) - len(visited)) if reasons & {"max_nodes", "max_paths", "max_hops"} else 0
    excluded_edges = max(0, len(unique_edges) - len(used_edges)) if reasons else 0
    return BlastRadiusResult(
        request.anchor,
        request.direction,
        tuple(paths),
        candidates,
        bool(reasons),
        ",".join(sorted(reasons)) or None,
        excluded_nodes,
        excluded_edges,
    )
