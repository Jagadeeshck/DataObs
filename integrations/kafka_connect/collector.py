from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .normalizer import normalize_connector


class KafkaConnectCollector:
    """Bounded collector that persists normalized summaries, never full configurations."""

    def __init__(self, client: Any, *, maximum_connectors: int = 1000):
        self.client = client
        self.maximum_connectors = maximum_connectors

    def collect(self) -> dict[str, Any]:
        names = sorted(self.client.connectors())
        selected = names[: self.maximum_connectors]
        observed_at = datetime.now(timezone.utc).isoformat()
        connectors = []
        errors = []
        for name in selected:
            try:
                normalized = normalize_connector(name, self.client.connector_config(name), self.client.status(name))
                normalized.pop("config", None)
                normalized["observed_at"] = observed_at
                connectors.append(normalized)
            except Exception as error:
                errors.append({"connector": name, "category": type(error).__name__})
        return {
            "connectors": connectors,
            "errors": errors,
            "continuation": selected[-1] if len(names) > len(selected) and selected else None,
            "data_status": "partial" if errors or len(names) > len(selected) else "complete",
        }
