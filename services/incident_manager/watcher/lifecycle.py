"""Elasticsearch Watcher lifecycle with an APScheduler fallback.

The manager owns the *alert-source* side only: it (de)registers a watch at
``_watcher/watch/<id>`` so Elasticsearch fires alerts natively. When the
Watcher feature is unavailable (e.g. a basic licence or a cluster without
Watcher enabled) it preserves the existing APScheduler polling path instead of
silently claiming native coverage.

Honesty semantics (per DataObs safety rules) are explicit and distinct:

* ``registered``          — ES accepted the watch; native Watcher is the source.
* ``deregistered``        — ES deleted the watch.
* ``fallback_scheduled``  — Watcher unavailable; APScheduler poll registered.
* ``unavailable``         — neither native Watcher nor a fallback could be set.

No notification is sent here; a firing watch is delivered through the existing
deduplicating incident pipeline via :mod:`.trigger`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

logger = logging.getLogger(__name__)

# Stable prefix so watch ids are tenant- and environment-scoped and never
# collide across tenants sharing a cluster.
_WATCH_ID_PREFIX = "dataobs"


def build_watch_id(tenant_id: str, environment: str, monitor_id: str) -> str:
    """Return the deterministic, tenant+environment scoped watch id."""
    for part, value in (("tenant_id", tenant_id), ("environment", environment), ("monitor_id", monitor_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{part} is required to build a watch id")
    return f"{_WATCH_ID_PREFIX}-{tenant_id}-{environment}-{monitor_id}"


class WatcherClient(Protocol):
    """Minimal surface of ``Elasticsearch.watcher`` used by the manager.

    The real ``elasticsearch`` client exposes these under ``client.watcher``.
    Tests inject a mock implementing just this protocol.
    """

    def put_watch(self, *, id: str, body: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def delete_watch(self, *, id: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class WatchRegistration:
    """A watch body plus the fallback schedule to use when Watcher is absent."""

    tenant_id: str
    environment: str
    monitor_id: str
    body: Mapping[str, Any]
    # Crontab string handed to the existing APScheduler path as the fallback.
    fallback_crontab: str = "*/5 * * * *"


@dataclass(frozen=True)
class WatchLifecycleResult:
    status: str
    watch_id: str
    source: str  # "watcher" | "apscheduler" | "none"
    detail: str | None = None


@dataclass
class _FallbackSchedule:
    watch_id: str
    crontab: str


class WatchLifecycleManager:
    """Register/deregister ES watches, falling back to APScheduler polling.

    ``watcher_client`` is optional: when it is ``None`` the manager records a
    fallback schedule instead of claiming native coverage. ``schedule_fallback``
    / ``cancel_fallback`` are injected callables so the manager never imports a
    concrete scheduler and stays unit-testable with no side effects.
    """

    def __init__(
        self,
        watcher_client: WatcherClient | None = None,
        *,
        schedule_fallback: Callable[[_FallbackSchedule], None] | None = None,
        cancel_fallback: Callable[[str], None] | None = None,
    ) -> None:
        self._watcher = watcher_client
        self._schedule_fallback = schedule_fallback
        self._cancel_fallback = cancel_fallback
        # Tracks ids we created so deregister is idempotent and scoped.
        self._registered: dict[str, str] = {}
        self._fallbacks: dict[str, _FallbackSchedule] = {}

    @property
    def registered_watch_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._registered))

    @property
    def fallback_watch_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._fallbacks))

    def register(self, registration: WatchRegistration) -> WatchLifecycleResult:
        """Create the native watch, or schedule the APScheduler fallback."""
        watch_id = build_watch_id(registration.tenant_id, registration.environment, registration.monitor_id)
        if self._watcher is not None:
            try:
                self._watcher.put_watch(id=watch_id, body=dict(registration.body))
                self._registered[watch_id] = registration.monitor_id
                logger.info("watcher registered", extra={"watch_id": watch_id, "source": "watcher"})
                return WatchLifecycleResult("registered", watch_id, "watcher")
            except Exception as exc:  # pragma: no cover - exercised via mock raising
                logger.warning(
                    "watcher put_watch failed; attempting fallback",
                    extra={"watch_id": watch_id, "error_type": type(exc).__name__},
                )
                return self._schedule(watch_id, registration, reason=type(exc).__name__)
        return self._schedule(watch_id, registration, reason="watcher_unavailable")

    def deregister(self, tenant_id: str, environment: str, monitor_id: str) -> WatchLifecycleResult:
        """Delete the native watch and/or cancel its fallback. Idempotent."""
        watch_id = build_watch_id(tenant_id, environment, monitor_id)
        had_native = watch_id in self._registered
        had_fallback = watch_id in self._fallbacks

        if self._watcher is not None and had_native:
            try:
                self._watcher.delete_watch(id=watch_id)
            except Exception as exc:  # pragma: no cover - exercised via mock raising
                logger.warning(
                    "watcher delete_watch failed",
                    extra={"watch_id": watch_id, "error_type": type(exc).__name__},
                )
            self._registered.pop(watch_id, None)

        if had_fallback:
            self._fallbacks.pop(watch_id, None)
            if self._cancel_fallback is not None:
                self._cancel_fallback(watch_id)

        if had_native:
            source = "watcher"
        elif had_fallback:
            source = "apscheduler"
        else:
            source = "none"
        detail = None if (had_native or had_fallback) else "no watch registered"
        return WatchLifecycleResult("deregistered", watch_id, source, detail)

    def _schedule(self, watch_id: str, registration: WatchRegistration, *, reason: str) -> WatchLifecycleResult:
        schedule = _FallbackSchedule(watch_id=watch_id, crontab=registration.fallback_crontab)
        if self._schedule_fallback is None:
            logger.warning(
                "no APScheduler fallback configured; alert source unavailable",
                extra={"watch_id": watch_id, "reason": reason},
            )
            return WatchLifecycleResult("unavailable", watch_id, "none", reason)
        self._schedule_fallback(schedule)
        self._fallbacks[watch_id] = schedule
        logger.info(
            "watcher fallback scheduled",
            extra={"watch_id": watch_id, "source": "apscheduler", "reason": reason},
        )
        return WatchLifecycleResult("fallback_scheduled", watch_id, "apscheduler", reason)
