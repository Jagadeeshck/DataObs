from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone


@dataclass
class EventWatermark:
    tenant_id: str
    environment: str
    last_event_timestamp: str | None = None
    last_event_id: str | None = None
    last_successful_processing: str | None = None
    overlap_window_seconds: int = 300
    worker_id: str | None = None
    fencing_token: int = 0
    documents_processed: int = 0
    consecutive_failures: int = 0

    def position(self) -> list[str] | None:
        if self.last_event_timestamp is None or self.last_event_id is None:
            return None
        return [self.last_event_timestamp, self.last_event_id]

    def document(self) -> dict[str, object]:
        return asdict(self)

    def committed(self, timestamp: str, event_id: str, count: int, worker_id: str, token: int) -> "EventWatermark":
        return replace(
            self,
            last_event_timestamp=timestamp,
            last_event_id=event_id,
            last_successful_processing=datetime.now(timezone.utc).isoformat(),
            worker_id=worker_id,
            fencing_token=token,
            documents_processed=self.documents_processed + count,
            consecutive_failures=0,
        )


# Backwards-compatible name for clients importing the original type.
Checkpoint = EventWatermark


def search_after(checkpoint: EventWatermark) -> list[str] | None:
    return checkpoint.position()
