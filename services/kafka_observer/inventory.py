from __future__ import annotations

from typing import Any


def inventory_projection(inventory: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded cluster/topic inventory portion of an admin probe."""
    return {key: inventory.get(key) for key in ("cluster_id", "controller_id", "brokers", "topics", "warnings")}
