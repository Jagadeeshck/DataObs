from __future__ import annotations

from datetime import timedelta

from .contracts import FloodDecision, FloodEvent, FloodState, FloodWindow
from .policy import V1_FLOOD_POLICY, FloodPolicy


def evaluate_flood(window: FloodWindow, event: FloodEvent, policy: FloodPolicy = V1_FLOOD_POLICY) -> FloodDecision:
    """Pure event-time evaluation. Callers durably persist the returned window/decision."""
    prior = window.state
    window.events.setdefault(event.event_id, event)  # replay never double-counts
    end = max(e.occurred_at for e in window.events.values())
    start = end - timedelta(seconds=policy.observation_seconds)
    active = sorted(
        (e for e in window.events.values() if start <= e.occurred_at <= end), key=lambda e: (e.occurred_at, e.event_id)
    )
    if len(window.events) > policy.maximum_events:
        retained = sorted(window.events.values(), key=lambda e: (e.occurred_at, e.event_id))[-policy.maximum_events :]
        window.events = {e.event_id: e for e in retained}
    count = len(active)
    assets = len({e.asset_id for e in active if e.asset_id})
    sources = len({e.source for e in active if e.source})
    rate = count / max(policy.observation_seconds / 60, 1 / 60)
    bypass = event.severity == "critical" or event.data_loss_risk
    reasons: list[str] = []
    if bypass:
        reasons.append("critical_severity" if event.severity == "critical" else "data_loss_risk")
        notification = "escalate"
    else:
        notification = "notify"
    flooding = (
        count >= policy.flooding_count
        or rate >= policy.event_rate_per_minute
        or assets >= policy.unique_asset_threshold
    )
    elevated = count >= policy.elevated_count or sources >= policy.unique_source_threshold
    if flooding:
        window.state = FloodState.FLOODING
        reasons.append("flood_threshold_reached")
    elif elevated:
        window.state = FloodState.ELEVATED
        reasons.append("elevated_threshold_reached")
    elif prior in {FloodState.FLOODING, FloodState.ELEVATED}:
        window.state = FloodState.RECOVERING
        reasons.append("below_threshold_recovering")
    elif prior == FloodState.RECOVERING and count > policy.hysteresis_count:
        window.state = FloodState.RECOVERING
        reasons.append("hysteresis_hold")
    else:
        window.state = FloodState.NORMAL
        reasons.append("below_threshold")
    if window.state == FloodState.FLOODING and not bypass:
        notification = "coalesce"
        window.suppressed_notification_count += 1
    return FloodDecision(
        prior,
        window.state,
        notification,
        tuple(reasons),
        {"count": count, "rate_per_minute": rate, "unique_assets": assets, "unique_sources": sources},
        {
            "elevated_count": policy.elevated_count,
            "flooding_count": policy.flooding_count,
            "rate_per_minute": policy.event_rate_per_minute,
            "unique_assets": policy.unique_asset_threshold,
        },
        start,
        end,
        policy.version,
        tuple(e.event_id for e in active[-50:]),
    )
