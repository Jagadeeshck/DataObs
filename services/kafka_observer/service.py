from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from integrations.kafka.admin_client import ReadOnlyAdmin

from .collector_registry import CapabilityBinding, validate_bindings
from .repository import ObserverRepository


class KafkaObserverService:
    def __init__(
        self,
        admin: ReadOnlyAdmin,
        checkpoints: Any,
        bindings: list[CapabilityBinding],
        *,
        comparison_mode: bool = False,
        repository: ObserverRepository | None = None,
    ):
        validate_bindings(bindings, comparison_mode=comparison_mode)
        self.admin = admin
        self.checkpoints = checkpoints
        self.bindings = bindings
        self.repository = repository

    def collect_once(self) -> dict[str, Any]:
        inventory = self.admin.inventory()
        fingerprint = hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()
        checkpoint = {
            "last_successful_collection": datetime.now(timezone.utc).isoformat(),
            "inventory_fingerprint": fingerprint,
            "cluster_id": inventory.get("cluster_id"),
            "errors": [],
            "backoff_seconds": 0,
        }
        self.checkpoints.save("dataobs_kafka_observer", checkpoint)
        if self.repository is not None:
            self.repository.save_collection("dataobs_kafka_observer", inventory, checkpoint)
        return {"inventory": inventory, "checkpoint": checkpoint}
