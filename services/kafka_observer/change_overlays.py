"""Non-causal, bounded change correlation helpers."""

from __future__ import annotations

from datetime import datetime

from packages.streaming.intelligence import ChangeOverlay


def correlate_change(
    *,
    anomaly_at: datetime,
    changed_at: datetime,
    change_type: str,
    changed_resource: str,
    summary: str,
    source: str,
    evidence_reference: str,
    maximum_distance_seconds: int = 86400,
) -> ChangeOverlay | None:
    distance = int(abs((anomaly_at - changed_at).total_seconds()))
    if distance > maximum_distance_seconds:
        return None
    safe_summary = "change observed near anomaly: " + " ".join(summary.split())[:200]
    return ChangeOverlay(
        change_type,
        changed_resource,
        changed_at,
        safe_summary,
        source,
        evidence_reference,
        distance,
        max(0.1, 1 - distance / maximum_distance_seconds),
        "measured",
    )
