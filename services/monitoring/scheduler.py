"""Deterministic schedule planning; durable state is owned by MonitorRepository."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class DueEvaluation:
    scheduled_for: datetime
    evaluation_key: str


def evaluation_key(
    tenant: str, environment: str, monitor_id: str, revision: int, scheduled_for: datetime, target: str
) -> str:
    canonical = "|".join(
        (tenant, environment, monitor_id, str(revision), scheduled_for.astimezone(timezone.utc).isoformat(), target)
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def interval_due(
    *,
    tenant: str,
    environment: str,
    monitor_id: str,
    revision: int,
    target: str,
    last_scheduled: datetime,
    now: datetime,
    interval: timedelta,
    max_catch_up: int = 24,
    jitter_seconds: int = 0,
) -> list[DueEvaluation]:
    if interval.total_seconds() <= 0 or max_catch_up < 1:
        raise ValueError("interval and max_catch_up must be positive")
    cursor = last_scheduled + interval
    windows: list[datetime] = []
    while cursor <= now and len(windows) < max_catch_up:
        windows.append(cursor)
        cursor += interval
    result = []
    for window in windows:
        key = evaluation_key(tenant, environment, monitor_id, revision, window, target)
        delay = random.Random(key).randint(0, jitter_seconds) if jitter_seconds else 0
        scheduled = window + timedelta(seconds=delay)
        result.append(
            DueEvaluation(scheduled, evaluation_key(tenant, environment, monitor_id, revision, window, target))
        )
    return result
