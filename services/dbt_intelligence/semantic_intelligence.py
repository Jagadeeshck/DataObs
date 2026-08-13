"""Bounded semantic dependency views (metadata only, never metric execution)."""

from typing import Any


def semantic_coverage(resources: list[dict[str, Any]]) -> dict[str, Any]:
    by_type = {
        kind: [item for item in resources if item["resource_type"] == kind]
        for kind in ("model", "semantic_model", "metric", "saved_query", "exposure")
    }
    modeled = {dependency for item in by_type["semantic_model"] for dependency in item.get("dependencies", [])}
    return {
        "models": len(by_type["model"]),
        "semantic_models": len(by_type["semantic_model"]),
        "metrics": len(by_type["metric"]),
        "saved_queries": len(by_type["saved_query"]),
        "exposures": len(by_type["exposure"]),
        "models_with_semantic_models": sum(item["unique_id"] in modeled for item in by_type["model"]),
        "metrics_without_description": sum(not item.get("description") for item in by_type["metric"]),
        "metrics_without_owner": sum(not item.get("owner") for item in by_type["metric"]),
        "semantic_models_without_group": sum(not item.get("group") for item in by_type["semantic_model"]),
    }
