"""Bounded, fenced recalculation queue used by Asset Trust workers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock


class FenceLost(RuntimeError):
    pass


@dataclass
class WorkItem:
    tenant_id: str
    environment: str
    asset_id: str
    reasons: set[str] = field(default_factory=set)
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    fencing_token: int = 0
    attempt_count: int = 0


class MemoryRecalculationQueue:
    """Reference implementation: deduplicated work, bounded claims, monotonic fences."""

    def __init__(self):
        self._items: dict[tuple[str, str, str], WorkItem] = {}
        self._lock = RLock()

    def request(self, tenant_id: str, environment: str, asset_id: str, reason: str):
        if not all((tenant_id, environment, asset_id, reason)):
            raise ValueError("scoped asset and reason are required")
        with self._lock:
            key = tenant_id, environment, asset_id
            item = self._items.setdefault(key, WorkItem(*key))
            item.reasons.add(reason)

    def claim(self, worker_id: str, *, limit: int = 100, lease_seconds: int = 60, now=None):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        now = now or datetime.now(timezone.utc)
        claimed = []
        with self._lock:
            for item in sorted(self._items.values(), key=lambda i: (i.requested_at, i.asset_id)):
                if item.lease_expires_at and item.lease_expires_at > now:
                    continue
                item.fencing_token += 1
                item.lease_owner = worker_id
                item.lease_expires_at = now + timedelta(seconds=lease_seconds)
                item.attempt_count += 1
                claimed.append(item)
                if len(claimed) == limit:
                    break
        return claimed

    def complete(self, item: WorkItem, worker_id: str, fencing_token: int):
        key = item.tenant_id, item.environment, item.asset_id
        with self._lock:
            current = self._items.get(key)
            if not current or current.lease_owner != worker_id or current.fencing_token != fencing_token:
                raise FenceLost("worker no longer owns the recalculation fence")
            del self._items[key]

    def health(self):
        now = datetime.now(timezone.utc)
        oldest = min((i.requested_at for i in self._items.values()), default=None)
        return {
            "assets_pending": len(self._items),
            "oldest_pending_age_seconds": (now - oldest).total_seconds() if oldest else 0,
        }
