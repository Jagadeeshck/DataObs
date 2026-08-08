from __future__ import annotations

from .models import ImpactRequest, utc_now
from .repository import LineageRepository
from .traversal import traverse

WEIGHTS = {
    "change_severity": 0.30,
    "relationship_strength": 0.20,
    "distance": 0.20,
    "path_confidence": 0.20,
    "criticality": 0.10,
}


def score(components: dict[str, float | None]) -> dict:
    available = {
        key: max(0.0, min(1.0, value)) for key, value in components.items() if value is not None and key in WEIGHTS
    }
    denominator = sum(WEIGHTS[key] for key in available)
    normalized = {key: WEIGHTS[key] / denominator for key in available} if denominator else {}
    value = round(100 * sum(available[key] * normalized[key] for key in available), 2) if normalized else None
    severity = (
        "unknown"
        if value is None
        else (
            "critical"
            if value >= 85
            else "high" if value >= 70 else "medium" if value >= 45 else "low" if value >= 20 else "informational"
        )
    )
    return {
        "impact_score": value,
        "severity": severity,
        "components": components,
        "normalized_weights": normalized,
        "formula": "100 * weighted_mean(available bounded components); unavailable components excluded",
    }


def analyse(
    repository: LineageRepository, tenant_id: str, environment: str, request: ImpactRequest, change: dict | None = None
) -> dict:
    graph = traverse(repository, tenant_id, environment, request)
    edge_confidence = {edge["target_asset_id"]: float(edge["confidence"]) for edge in graph.edges}
    severity = str((change or {}).get("severity", ""))
    severity_value = {"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.3}.get(severity)
    affected = []
    for node in graph.nodes[1:]:
        distance = int(node["depth"])
        confidence = edge_confidence.get(node["asset_id"], 0.35)
        scoring = score(
            {
                "change_severity": severity_value,
                "relationship_strength": 1.0 if distance == 1 else 0.6,
                "distance": 1 / (distance + 1),
                "path_confidence": confidence,
                "criticality": None,
            }
        )
        affected.append(
            {
                **node,
                "relationship": "direct" if distance == 1 else "transitive",
                "confidence": confidence,
                "reason_codes": ["structurally_downstream", "no_direct_failure_evidence_observed"],
                **scoring,
            }
        )
    evaluation = {
        "analysis_id": request.analysis_id(tenant_id, environment),
        "root_entity": {"asset_id": request.root_asset_id, "column": request.root_column},
        "triggering_change": request.schema_change_id,
        "evaluated_at": utc_now(),
        "affected_assets": affected,
        "affected_columns": [],
        "affected_jobs": [],
        "affected_data_products": [],
        "affected_quality_monitors": [],
        "affected_owners": [],
        "linked_incidents": [],
        "directly_affected_count": sum(x["relationship"] == "direct" for x in affected),
        "transitively_affected_count": sum(x["relationship"] == "transitive" for x in affected),
        "paths": graph.paths,
        "cycles": graph.cycles,
        "truncated": graph.truncated,
        "warnings": list(graph.warnings),
        "data_status": "partial" if graph.truncated else "available",
        "confidence": min((x["confidence"] for x in affected), default=0.0),
        "missing_evidence": ["contextual overlays are unavailable"] if request.include_contextual_overlays else [],
        "schema_version": "v1",
    }
    repository.append_impact_evaluation(tenant_id, environment, evaluation)
    return evaluation
