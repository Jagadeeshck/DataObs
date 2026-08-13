"""Declared dependency projection and provenance-preserving reconciliation."""

from __future__ import annotations

from hashlib import sha256
from typing import Any


def declared_edges(resources: list[dict[str, Any]], limit: int = 100_000) -> list[dict[str, Any]]:
    known = {item["unique_id"] for item in resources}
    edges = []
    for target in resources:
        for source in target.get("dependencies", []):
            if source not in known:
                continue
            relationship = (
                "semantic_dependency"
                if target["resource_type"] in {"semantic_model", "metric", "saved_query"}
                else "consumer_dependency" if target["resource_type"] == "exposure" else "declared_model_dependency"
            )
            edge_key = f"{source}\x1f{target['unique_id']}\x1f{relationship}"
            edges.append(
                {
                    "edge_id": "dbt_edge_" + sha256(edge_key.encode()).hexdigest(),
                    "source": source,
                    "target": target["unique_id"],
                    "edge_type": relationship,
                    "provider": "dbt",
                    "evidence_type": "declared_dependency",
                    "relationship": "declared",
                }
            )
            if len(edges) >= limit:
                return edges
    return edges


def reconcile_lineage(declared: list[dict[str, Any]], observed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    declared_pairs = {(item["source"], item["target"]): item for item in declared}
    observed_pairs = {(item["source"], item["target"]): item for item in observed}
    return [
        {
            "source": pair[0],
            "target": pair[1],
            "state": (
                "declared_and_observed"
                if pair in declared_pairs and pair in observed_pairs
                else "declared_only" if pair in declared_pairs else "observed_only"
            ),
            "provenance": [
                name
                for name, values in (("dbt_manifest", declared_pairs), ("runtime", observed_pairs))
                if pair in values
            ],
        }
        for pair in sorted(set(declared_pairs) | set(observed_pairs))
    ]
