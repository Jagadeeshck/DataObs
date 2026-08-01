"""Bounded, deterministic pathway assembly and explainable intelligence.

The functions in this module deliberately operate on canonical projections only;
raw span attributes and Kafka payloads are never accepted or retained.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

EVIDENCE_CONFIDENCE = {
    "trace_observed": 0.95,
    "openlineage_observed": 0.9,
    "kafka_metric_observed": 0.85,
    "catalog_declared": 0.7,
    "structural": 0.65,
    "inferred": 0.4,
    "unknown": 0.0,
}
HEALTH_ORDER = {"not_configured": -1, "unknown": 0, "healthy": 1, "warning": 2, "degraded": 3, "critical": 4}


def confidence_for(evidence: Iterable[str]) -> float:
    """Combine independent coverage conservatively without exceeding direct proof."""
    values = sorted({EVIDENCE_CONFIDENCE.get(item, 0.0) for item in evidence}, reverse=True)
    if not values:
        return 0.0
    result = values[0]
    for value in values[1:]:
        result += (1.0 - result) * value * 0.25
    return round(min(result, 0.99), 3)


def canonical_id(prefix: str, tenant: str, environment: str, *parts: str) -> str:
    raw = "\0".join([tenant, environment, *[str(part).strip() for part in parts]])
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"


def canonical_node(tenant: str, environment: str, node_type: str, name: str, **values: Any) -> dict[str, Any]:
    namespace = str(values.get("qualified_name") or name)
    evidence = list(dict.fromkeys(values.get("evidence_refs", [])))[:50]
    return {
        "node_id": canonical_id("pnode", tenant, environment, node_type, namespace),
        "tenant_id": tenant,
        "environment": environment,
        "node_type": node_type,
        "name": name,
        "qualified_name": namespace,
        "platform": values.get("platform", "unknown"),
        "cluster_id": values.get("cluster_id"),
        "integration_id": values.get("integration_id"),
        "owner_team": values.get("owner_team"),
        "business_service": values.get("business_service"),
        "first_seen": values.get("first_seen"),
        "last_seen": values.get("last_seen"),
        "active": values.get("active", True),
        "source_coverage": list(dict.fromkeys(values.get("source_coverage", []))),
        "evidence_refs": evidence,
        "schema_version": "v1",
    }


def canonical_edge(
    tenant: str, environment: str, source: str, destination: str, edge_type: str, **values: Any
) -> dict[str, Any]:
    coverage = list(dict.fromkeys(values.get("source_coverage", [values.get("evidence_type", "unknown")])))
    return {
        "edge_id": canonical_id("pedge", tenant, environment, source, destination, edge_type),
        "tenant_id": tenant,
        "environment": environment,
        "source_node_id": source,
        "destination_node_id": destination,
        "edge_type": edge_type,
        "messaging_system": values.get("messaging_system"),
        "cluster_id": values.get("cluster_id"),
        "topic_id": values.get("topic_id"),
        "consumer_group_id": values.get("consumer_group_id"),
        "first_seen": values.get("first_seen"),
        "last_seen": values.get("last_seen"),
        "observation_count": values.get("observation_count", 1),
        "active": values.get("active", True),
        "confidence": confidence_for(coverage),
        "coverage": values.get("coverage", "partial" if edge_type == "partial_edge" else "complete"),
        "health": values.get("health", "unknown"),
        "source_coverage": coverage,
        "evidence_refs": list(dict.fromkeys(values.get("evidence_refs", [])))[:50],
        "metrics": values.get("metrics", {}),
        "schema_version": "v1",
    }


def assemble_pathways(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    active_only: bool = True,
    minimum_confidence: float = 0.0,
    max_hops: int = 8,
    max_nodes: int = 500,
    max_edges: int = 1000,
    max_pathways: int = 200,
) -> list[dict[str, Any]]:
    """Traverse only from graph roots, cycle safely, and emit bounded terminal paths."""
    selected = [
        e for e in edges if (not active_only or e.get("active", True)) and e.get("confidence", 0) >= minimum_confidence
    ]
    excluded = len(edges) - len(selected)
    selected = selected[:max_edges]
    node_map = {n["node_id"]: n for n in nodes[:max_nodes]}
    outgoing: dict[str, list[dict[str, Any]]] = {}
    incoming: set[str] = set()
    for edge in selected:
        outgoing.setdefault(edge["source_node_id"], []).append(edge)
        incoming.add(edge["destination_node_id"])
    roots = sorted(set(outgoing) - incoming) or sorted(outgoing)
    result: list[dict[str, Any]] = []

    def emit(path_edges: list[dict[str, Any]], cycle: bool = False) -> None:
        if not path_edges or len(result) >= max_pathways:
            return
        edge_ids = [edge["edge_id"] for edge in path_edges]
        node_ids = [path_edges[0]["source_node_id"], *[edge["destination_node_id"] for edge in path_edges]]
        partial = cycle or any(
            edge.get("coverage") == "partial" or edge.get("edge_type") == "partial_edge" for edge in path_edges
        )
        evidence = list(dict.fromkeys(ref for edge in path_edges for ref in edge.get("evidence_refs", [])))[:100]
        coverage = list(dict.fromkeys(source for edge in path_edges for source in edge.get("source_coverage", [])))
        result.append(
            {
                "pathway_id": canonical_id(
                    "pathway", path_edges[0].get("tenant_id", ""), path_edges[0].get("environment", ""), *edge_ids
                ),
                "node_ids": node_ids,
                "edge_ids": edge_ids,
                "classification": "partial" if partial else "complete",
                "truncated": cycle or len(path_edges) >= max_hops,
                "excluded_edge_count": excluded,
                "source_coverage": coverage,
                "evidence_refs": evidence,
                "confidence": min((edge.get("confidence", 0.0) for edge in path_edges), default=0.0),
                "nodes": [node_map[item] for item in node_ids if item in node_map],
            }
        )

    def walk(current: str, path: list[dict[str, Any]], visited: set[str]) -> None:
        choices = sorted(outgoing.get(current, []), key=lambda item: item["edge_id"])
        if not choices or len(path) >= max_hops:
            emit(path)
            return
        for edge in choices:
            destination = edge["destination_node_id"]
            if destination in visited:
                emit(path + [edge], cycle=True)
            else:
                walk(destination, path + [edge], visited | {destination})

    for root in roots:
        walk(root, [], {root})
        if len(result) >= max_pathways:
            break
    if len(result) == max_pathways:
        result[-1]["truncated"] = True
    return result


def pathway_health(edges: list[dict[str, Any]], *, partial: bool = False, stale: bool = False) -> dict[str, Any]:
    states = [edge.get("health", "unknown") for edge in edges if edge.get("active", True)]
    health = max(states, key=lambda state: HEALTH_ORDER.get(state, 0)) if states else "unknown"
    missing = [] if states and all(state != "unknown" for state in states) else ["edge_health"]
    reasons = [f"edge_{state}" for state in sorted(set(states)) if state not in {"healthy", "unknown"}]
    if partial:
        reasons.append("partial_coverage")
        missing.append("complete_topology")
    confidence = min((edge.get("confidence", 0.0) for edge in edges), default=0.0)
    if stale:
        confidence *= 0.5
        reasons.append("stale_evidence")
    return {
        "health": health,
        "reason_codes": reasons,
        "confidence": round(confidence, 3),
        "data_status": "stale" if stale else ("partial" if partial or missing else "complete"),
        "missing_inputs": sorted(set(missing)),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def latency(edges: list[dict[str, Any]]) -> dict[str, Any]:
    correlated = [e.get("metrics", {}).get("end_to_end_latency") for e in edges]
    correlated = [v for v in correlated if isinstance(v, dict) and v.get("correlation_id")]
    if correlated:
        values = correlated[-1]
        return {
            "method": "trace_derived",
            "p50_ms": values.get("p50_ms"),
            "p95_ms": values.get("p95_ms"),
            "p99_ms": values.get("p99_ms"),
            "sample_count": values.get("sample_count", 0),
            "missing_segments": [],
            "confidence": 0.95,
        }
    samples = [e.get("metrics", {}).get("latency_ms") for e in edges]
    samples = [value for value in samples if isinstance(value, (int, float))]
    if samples:
        ordered = sorted(samples)

        def pick(percentile: float) -> float:
            return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * percentile))]

        return {
            "method": "edge_estimate",
            "p50_ms": pick(0.5),
            "p95_ms": pick(0.95),
            "p99_ms": pick(0.99),
            "sample_count": len(samples),
            "missing_segments": [
                e["edge_id"] for e in edges if not isinstance(e.get("metrics", {}).get("latency_ms"), (int, float))
            ],
            "confidence": 0.6,
        }
    return {
        "method": "unavailable",
        "p50_ms": None,
        "p95_ms": None,
        "p99_ms": None,
        "sample_count": 0,
        "missing_segments": [e.get("edge_id") for e in edges],
        "confidence": 0.0,
    }


def bottlenecks(edges: list[dict[str, Any]], view: str) -> list[dict[str, Any]]:
    metric = {
        "latency": "latency_ms",
        "reliability": "error_rate",
        "backlog": "lag_messages",
        "retention_risk": "retention_risk",
    }[view]
    values = [(e, e.get("metrics", {}).get(metric)) for e in edges]
    values = [(e, float(v)) for e, v in values if isinstance(v, (int, float)) and v >= 0]
    total = sum(value for _, value in values)
    if len(values) < 2 or total <= 0:
        return []
    return [
        {
            "edge_id": edge["edge_id"],
            "view": view,
            "contribution_percentage": round(value * 100 / total, 2),
            "absolute_contribution": value,
            "calculation_method": f"share_of_observed_{metric}",
            "missing_inputs": [],
            "health_explanation": "Candidate contribution; this is not a root-cause claim",
            "confidence": edge.get("confidence", 0.0),
        }
        for edge, value in sorted(values, key=lambda item: item[1], reverse=True)
    ]


def compare_windows(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_edges, after_edges = set(before.get("edge_ids", [])), set(after.get("edge_ids", []))
    metrics = set(before.get("metrics", {})) | set(after.get("metrics", {}))
    deltas = {
        key: (after["metrics"][key] - before["metrics"][key])
        for key in metrics
        if isinstance(before.get("metrics", {}).get(key), (int, float))
        and isinstance(after.get("metrics", {}).get(key), (int, float))
    }
    sufficient = bool(before.get("sample_count", 0) and after.get("sample_count", 0))
    changes = sorted(after_edges ^ before_edges)
    return {
        "metric_deltas": deltas,
        "new_edges": sorted(after_edges - before_edges),
        "removed_edges": sorted(before_edges - after_edges),
        "sample_sufficient": sufficient,
        "suspected_correlated_changes": changes if sufficient else [],
        "confidence": 0.8 if sufficient else 0.0,
        "warnings": ["Correlation does not establish causation"] + ([] if sufficient else ["Insufficient samples"]),
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
