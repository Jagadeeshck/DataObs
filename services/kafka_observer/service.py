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
        connect_collector: Any | None = None,
        schema_collector: Any | None = None,
    ):
        validate_bindings(bindings, comparison_mode=comparison_mode)
        self.admin = admin
        self.checkpoints = checkpoints
        self.bindings = bindings
        self.repository = repository
        self.connect_collector = connect_collector
        self.schema_collector = schema_collector

    def collect_capability(self, capability: str) -> dict[str, Any]:
        attempted = datetime.now(timezone.utc).isoformat()
        previous = self.checkpoints.load(capability) or {}
        try:
            if capability == "inventory":
                payload = self.admin.inventory()
                if self.repository is not None:
                    self.repository.save_collection(capability, payload, {})
            elif capability == "groups":
                inventory = self.admin.inventory()
                payload = {"cluster_id": inventory.get("cluster_id"), "groups": inventory.get("consumer_groups", [])}
            elif capability == "offsets":
                payload = self.admin.offsets(maximum=100_000)
            elif capability == "connectors":
                payload = (
                    self.connect_collector.collect()
                    if self.connect_collector
                    else {"data_status": "not_configured", "connectors": []}
                )
            elif capability == "schemas":
                payload = (
                    self.schema_collector.collect()
                    if self.schema_collector
                    else {"data_status": "not_configured", "schemas": []}
                )
            else:
                raise ValueError(f"unsupported collection capability: {capability}")
        except Exception as error:
            checkpoint = previous | {
                "last_attempted_collection": attempted,
                "last_failure_category": type(error).__name__,
                "consecutive_failure_count": int(previous.get("consecutive_failure_count", 0)) + 1,
            }
            self.checkpoints.save(capability, checkpoint)
            raise
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        checkpoint = {
            "last_attempted_collection": attempted,
            "last_successful_collection": datetime.now(timezone.utc).isoformat(),
            "collection_fingerprint": fingerprint,
            "source_cursor": payload.get("continuation"),
            "last_failure_category": None,
            "consecutive_failure_count": 0,
            "retry_after": None,
        }
        self.checkpoints.save(capability, checkpoint)
        return {
            "capability": capability,
            "data_status": payload.get("data_status", "available"),
            "result": payload,
            "checkpoint": checkpoint,
        }

    def collect_once(self) -> dict[str, Any]:
        results = {
            name: self.collect_capability(name) for name in ("inventory", "groups", "offsets", "connectors", "schemas")
        }
        return {
            "data_status": "partial" if any(v["data_status"] != "available" for v in results.values()) else "available",
            "capabilities": results,
        }
