"""Redaction-safe, bounded platform health contracts."""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Awaitable, Callable


class HealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DISABLED = "disabled"


class Criticality(StrEnum):
    LIVENESS = "required_for_liveness"
    STARTUP = "required_for_startup"
    READINESS = "required_for_readiness"
    OPTIONAL = "optional"
    INFORMATIONAL = "informational"


@dataclass(frozen=True)
class HealthCheck:
    name: str
    state: HealthState
    criticality: Criticality
    reason_code: str
    last_checked: str
    duration_seconds: float
    remediation_code: str | None = None


@dataclass(frozen=True)
class HealthReport:
    state: HealthState
    component: str
    checks: tuple[HealthCheck, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "component": self.component,
            "checks": [asdict(item) for item in self.checks],
        }


class CachedHealthCheck:
    """Coalesce concurrent probes and cache their safe result for a short TTL."""

    def __init__(self, ttl_seconds: float = 5.0, timeout_seconds: float = 2.0) -> None:
        self.ttl_seconds = ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._cached: HealthCheck | None = None
        self._cached_at = 0.0
        self._lock = asyncio.Lock()

    async def run(
        self,
        name: str,
        criticality: Criticality,
        probe: Callable[[], Awaitable[tuple[HealthState, str]]],
    ) -> HealthCheck:
        now = time.monotonic()
        if self._cached and now - self._cached_at < self.ttl_seconds:
            return self._cached
        async with self._lock:
            now = time.monotonic()
            if self._cached and now - self._cached_at < self.ttl_seconds:
                return self._cached
            started = time.monotonic()
            try:
                state, reason = await asyncio.wait_for(probe(), timeout=self.timeout_seconds)
            except TimeoutError:
                state, reason = HealthState.UNHEALTHY, "dependency_timeout"
            except Exception:
                state, reason = HealthState.UNHEALTHY, "dependency_unavailable"
            self._cached = HealthCheck(
                name=name,
                state=state,
                criticality=criticality,
                reason_code=reason,
                last_checked=datetime.now(UTC).isoformat(),
                duration_seconds=round(time.monotonic() - started, 6),
            )
            self._cached_at = time.monotonic()
            return self._cached


def aggregate(component: str, checks: list[HealthCheck]) -> HealthReport:
    required_failed = any(
        c.state in {HealthState.UNHEALTHY, HealthState.UNKNOWN}
        and c.criticality in {Criticality.LIVENESS, Criticality.STARTUP, Criticality.READINESS}
        for c in checks
    )
    optional_failed = any(c.state in {HealthState.UNHEALTHY, HealthState.UNKNOWN, HealthState.DEGRADED} for c in checks)
    state = (
        HealthState.UNHEALTHY if required_failed else HealthState.DEGRADED if optional_failed else HealthState.HEALTHY
    )
    return HealthReport(state, component, tuple(checks))
