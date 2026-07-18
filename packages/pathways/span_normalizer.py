from __future__ import annotations

import hashlib
from typing import Any


def _first(document: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value: Any = document
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if value is not None:
            return value
    return None


def normalize_span(document: dict[str, Any], *, retain_message_key: bool = False) -> dict[str, Any]:
    raw_key = _first(document, "messaging.kafka.message.key", "labels.messaging_kafka_message_key")
    result = {
        "messaging.system": _first(document, "messaging.system", "labels.messaging_system") or "kafka",
        "messaging.operation.type": _first(document, "messaging.operation.type", "messaging.operation", "span.subtype"),
        "messaging.destination.name": _first(
            document, "messaging.destination.name", "messaging.destination", "destination.resource"
        ),
        "messaging.destination.partition.id": _first(
            document, "messaging.destination.partition.id", "messaging.kafka.partition"
        ),
        "messaging.consumer.group.name": _first(
            document, "messaging.consumer.group.name", "messaging.kafka.consumer.group"
        ),
        "service.name": _first(document, "service.name", "service.name.keyword"),
        "service.namespace": _first(document, "service.namespace"),
        "service.version": _first(document, "service.version"),
        "deployment.environment.name": _first(document, "deployment.environment.name", "service.environment"),
        "trace_id": _first(document, "trace_id", "trace.id"),
        "span_id": _first(document, "span_id", "span.id"),
        "parent_span_id": _first(document, "parent_span_id", "parent.id"),
        "span.kind": _first(document, "span.kind"),
        "@timestamp": _first(document, "@timestamp"),
        "links": document.get("links", document.get("span", {}).get("links", [])),
    }
    if raw_key is not None:
        result["messaging.kafka.message.key"] = (
            raw_key if retain_message_key else hashlib.sha256(str(raw_key).encode()).hexdigest()
        )
        result["messaging.kafka.message.key_protection"] = "raw-approved" if retain_message_key else "sha256"
    return {k: v for k, v in result.items() if v is not None}
