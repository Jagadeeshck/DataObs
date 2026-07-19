from __future__ import annotations

from typing import Any


def broker_metric_status(metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    if not metrics:
        return {"data_status": "not_configured", "metrics": [], "missing_inputs": ["broker_metric_source"]}
    return {"data_status": "complete", "metrics": metrics, "missing_inputs": []}
