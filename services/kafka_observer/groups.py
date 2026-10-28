from __future__ import annotations

from typing import Any


def group_projection(inventory: dict[str, Any]) -> dict[str, Any]:
    groups = inventory.get("consumer_groups", [])
    warnings = inventory.get("warnings", [])
    unavailable = any("consumer group inventory unavailable" in warning for warning in warnings)
    return {
        "cluster_id": inventory.get("cluster_id"),
        "groups": groups,
        "count": None if unavailable else len(groups),
        "data_status": "source_unavailable" if unavailable else "partial" if warnings else "complete",
    }
