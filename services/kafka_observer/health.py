def group_health(
    *,
    state: str | None,
    member_count: int | None,
    lag: int | None,
    lag_velocity: float | None,
    rebalance_count: int = 0,
) -> dict:
    if state is None or member_count is None:
        return {"state": "source_unavailable", "reasons": ["group state or membership unavailable"], "confidence": 0.0}
    normalized = state.lower()
    if "preparing" in normalized or "completing" in normalized:
        result = "rebalancing"
    elif rebalance_count >= 5:
        result = "unstable"
    elif member_count == 0:
        result = "no_consumers"
    elif lag is None:
        result = "unknown"
    elif lag == 0:
        result = "healthy"
    elif lag_velocity is not None and lag_velocity < 0:
        result = "catching_up"
    elif lag_velocity == 0:
        result = "stalled"
    else:
        result = "lagging"
    return {
        "state": result,
        "reasons": [f"broker_state={state}", f"members={member_count}", f"lag={lag}"],
        "confidence": 0.9 if lag is not None else 0.4,
    }
