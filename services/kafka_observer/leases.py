from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol


class LeaseRepository(Protocol):
    def acquire_lease(self, name: str, owner: str, expires_at: str) -> bool: ...
    def release_lease(self, name: str, owner: str) -> None: ...


class DurableLeases:
    def __init__(self, repository: LeaseRepository):
        self.repository = repository

    def acquire(self, name: str, owner: str, duration_seconds: float) -> bool:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=max(duration_seconds, 1))
        return self.repository.acquire_lease(name, owner, expiry.isoformat())

    def renew(self, name: str, owner: str, duration_seconds: float) -> bool:
        return self.acquire(name, owner, duration_seconds)

    def release(self, name: str, owner: str) -> None:
        self.repository.release_lease(name, owner)


class MemoryLeaseRepository:
    """Deterministic test double; production uses Elasticsearch optimistic concurrency."""

    def __init__(self):
        self.values: dict[str, dict[str, Any]] = {}

    def acquire_lease(self, name: str, owner: str, expires_at: str) -> bool:
        now = datetime.now(timezone.utc)
        current = self.values.get(name)
        if current and current["owner"] != owner and datetime.fromisoformat(current["expires_at"]) > now:
            return False
        self.values[name] = {"owner": owner, "expires_at": expires_at}
        return True

    def release_lease(self, name: str, owner: str) -> None:
        if self.values.get(name, {}).get("owner") == owner:
            self.values.pop(name, None)
