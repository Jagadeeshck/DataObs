from __future__ import annotations

from typing import Any


def group_projection(inventory: dict[str, Any]) -> dict[str, Any]:
    groups = inventory.get("consumer_groups", [])
    return {"cluster_id": inventory.get("cluster_id"), "groups": groups, "count": len(groups)}
