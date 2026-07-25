from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

SAFE_EVENT_TYPES = {
    "stream.cluster.updated",
    "stream.resource.updated",
    "stream.partition.updated",
    "stream.health.changed",
    "stream.throughput.updated",
    "consumer_group.updated",
    "consumer_group.lag.changed",
    "consumer_group.retention_risk.changed",
    "consumer_group.rebalance",
    "stream_connector.updated",
    "stream_schema.changed",
    "stream_configuration.changed",
    "stream_monitor.updated",
    "stream_recommendation.updated",
    "stream_incident.updated",
    "stream_rca.updated",
    "stream_action.updated",
}
SAFE_PAYLOAD_FIELDS = {"resource_id", "data_status", "observed_at", "reason_codes", "changed_fields"}


@dataclass(frozen=True)
class StreamEvent:
    event_id: int
    tenant: str
    environment: str
    event_type: str
    payload: dict[str, Any]
    observed_at: str


class EventReplay:
    def __init__(self, maximum: int = 500) -> None:
        self._events: deque[StreamEvent] = deque(maxlen=maximum)
        self._lock = Lock()
        self._next = 1

    def publish(self, tenant: str, environment: str, event_type: str, payload: dict[str, Any]) -> StreamEvent:
        if event_type not in SAFE_EVENT_TYPES:
            raise ValueError("event type is not allowlisted")
        safe = {key: value for key, value in payload.items() if key in SAFE_PAYLOAD_FIELDS}
        with self._lock:
            event = StreamEvent(
                self._next, tenant, environment, event_type, safe, datetime.now(timezone.utc).isoformat()
            )
            self._next += 1
            self._events.append(event)
            return event

    def replay(self, tenant: str, environment: str, after: int = 0) -> list[StreamEvent]:
        return [
            event
            for event in self._events
            if event.event_id > after and event.tenant == tenant and event.environment == environment
        ]
