from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from packages.streaming.redaction import redact_mapping


@dataclass(frozen=True)
class CollectionError:
    collector: str
    source: str
    category: str
    retryable: bool
    fingerprint: str
    first_observed: str
    last_observed: str
    retry_count: int
    message: str
    request_id: str | None = None
    trace_id: str | None = None

    @classmethod
    def from_exception(cls, collector: str, source: str, error: Exception, retry_count: int) -> "CollectionError":
        now = datetime.now(timezone.utc).isoformat()
        category = type(error).__name__
        # Exception strings routinely contain URLs and client configuration.  Persist
        # the stable type, never an arbitrary upstream message.
        safe_message = f"collection failed ({category})"
        fingerprint = hashlib.sha256(f"{collector}:{source}:{category}:{safe_message}".encode()).hexdigest()
        return cls(collector, source, category, True, fingerprint, now, now, retry_count, safe_message)

    def document(self) -> dict[str, object]:
        return asdict(self)
