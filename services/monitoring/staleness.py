"""Shared, absence-preserving monitor staleness semantics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from packages.domain_model.monitor import MonitorState

_ACTIVE = {MonitorState.ENABLED, MonitorState.ACTIVE, MonitorState.LEARNING, MonitorState.DEGRADED, MonitorState.ERROR}


@dataclass(frozen=True)
class Staleness:
    stale: bool | None
    confidence: float
    reason_codes: tuple[str, ...]


def interval_seconds(interval: str) -> int:
    match = re.fullmatch(r"([1-9][0-9]*)(m|h|d)", interval)
    if not match:
        raise ValueError("invalid bounded schedule interval")
    return int(match.group(1)) * {"m": 60, "h": 3600, "d": 86400}[match.group(2)]


def monitor_staleness(
    *,
    state: MonitorState | str,
    interval: str,
    last_observation_at: datetime | None,
    now: datetime | None = None,
    grace_multiplier: float = 2.0,
    runtime_available: bool | None = None,
) -> Staleness:
    """Classify freshness without equating staleness and monitor failure."""
    state = MonitorState(state)
    if state not in _ACTIVE:
        return Staleness(None, 1.0, ("staleness_not_applicable",))
    grace_multiplier = min(10.0, max(1.0, grace_multiplier))
    confidence = 1.0 if runtime_available is not None else 0.6
    reasons: list[str] = [] if runtime_available is not None else ["runtime_evidence_missing"]
    if last_observation_at is None:
        return Staleness(None, confidence, tuple([*reasons, "observation_missing"]))
    current = now or datetime.now(timezone.utc)
    if last_observation_at.tzinfo is None:
        last_observation_at = last_observation_at.replace(tzinfo=timezone.utc)
    stale = current - last_observation_at > timedelta(seconds=interval_seconds(interval) * grace_multiplier)
    return Staleness(stale, confidence, tuple([*reasons, "schedule_grace_exceeded"] if stale else reasons))
