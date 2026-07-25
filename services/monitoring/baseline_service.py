"""Deterministic immutable monitor baselines without future leakage."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any, Sequence

from services.monitoring.definition_events import canonical_checksum


def build_baseline(
    *,
    tenant_id: str,
    environment: str,
    monitor_id: str,
    definition_revision: int,
    observations: Sequence[Any],
    method: str = "mad",
    sensitivity: str = "medium",
    minimum_samples: int = 12,
    reset_reason: str | None = None,
    supersedes: str | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    cutoff = as_of or datetime.now(timezone.utc)
    eligible = [o for o in observations if o.observed_at < cutoff and o.value is not None and not o.missing_data]
    values = [float(o.value) for o in eligible]
    center = median(values) if values else None
    deviations = [abs(v - center) for v in values] if center is not None else []
    spread = median(deviations) if deviations else 0.0
    factor = {"low": 4.5, "medium": 3.5, "high": 2.5}[sensitivity]
    state = "mature" if len(values) >= minimum_samples else ("provisional" if values else "learning")
    core: dict[str, Any] = {
        "tenant_id": tenant_id,
        "environment": environment,
        "monitor_id": monitor_id,
        "definition_revision": definition_revision,
        "method": method,
        "sensitivity": sensitivity,
        "history_start": eligible[0].observed_at.isoformat() if eligible else None,
        "history_end": eligible[-1].observed_at.isoformat() if eligible else None,
        "sample_count": len(values),
        "expected_minimum": center - factor * spread if center is not None else None,
        "expected_maximum": center + factor * spread if center is not None else None,
        "confidence": min(1.0, len(values) / minimum_samples),
        "cold_start_state": state,
        "excluded_periods": [],
        "source_evaluation_keys": [],
        "reset_reason": reset_reason,
        "supersedes": supersedes,
    }
    core["baseline_version"] = canonical_checksum(core)
    core["created_at"] = cutoff.isoformat()
    return core
