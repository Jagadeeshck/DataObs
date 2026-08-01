from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta

from .contracts import FloodDecision, FloodEvent, FloodState, FloodWindow
from .policy import V1_FLOOD_POLICY, FloodPolicy


def evaluate_flood(
    window: FloodWindow,
    event: FloodEvent,
    policy: FloodPolicy = V1_FLOOD_POLICY,
    *,
    quiet_at: datetime | None = None,
) -> tuple[FloodDecision, FloodWindow]:
    """Return a decision and new state without mutating caller-owned state."""
    window = deepcopy(window)
    prior = window.state
    replay = event.event_id in window.events
    existing = tuple(window.events.values())
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
    bypass_reasons = []
    if event.severity == "critical":
        bypass_reasons.append("critical_severity")
    if event.data_loss_risk:
        bypass_reasons.append("suspected_data_loss")
    if event.retention_loss_risk:
        bypass_reasons.append("imminent_retention_loss")
    if event.business_impact_confirmed:
        bypass_reasons.append("confirmed_business_impact")
    if not event.representative_valid:
        bypass_reasons.append("invalid_representative_incident")
    comparisons = (
        (event.data_products, (v for e in existing for v in e.data_products), "new_critical_data_product"),
        (event.business_services, (v for e in existing for v in e.business_services), "new_critical_business_service"),
        ((event.region,) if event.region else (), (e.region for e in existing), "new_region"),
        ((event.account,) if event.account else (), (e.account for e in existing), "new_account"),
        ((event.cluster,) if event.cluster else (), (e.cluster for e in existing), "new_cluster"),
        (
            (event.failure_family,) if event.failure_family else (),
            (e.failure_family for e in existing),
            "new_failure_family",
        ),
    )
    for incoming, previous, code in comparisons:
        if incoming and not set(incoming).issubset({v for v in previous if v}):
            bypass_reasons.append(code)
    previous_assets = {e.asset_id for e in existing if e.asset_id}
    if event.asset_id and previous_assets and event.asset_id not in previous_assets:
        bypass_reasons.append("materially_expanded_asset_scope")
    bypass = bool(bypass_reasons)
    reasons: list[str] = []
    if bypass:
        reasons.extend(bypass_reasons)
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
        quiet_elapsed = bool(
            prior == FloodState.RECOVERING
            and quiet_at is not None
            and window.last_transition_at is not None
            and quiet_at >= window.last_transition_at + timedelta(seconds=policy.quiet_period_seconds)
        )
        window.state = FloodState.CLOSED if quiet_elapsed else FloodState.NORMAL
        reasons.append("quiet_period_closed" if quiet_elapsed else "below_threshold")
    if window.state == FloodState.FLOODING and not bypass and not replay:
        notification = "coalesce"
        window.suppressed_notification_count += 1
    if window.state != prior:
        window.last_transition_at = end
    return (
        FloodDecision(
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
        ),
        window,
    )
