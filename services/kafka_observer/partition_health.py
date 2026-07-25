def replication_health(*, replicas: list[int], isr: list[int], leader_id: int | None) -> dict:
    offline = leader_id is None or leader_id < 0
    missing = sorted(set(replicas) - set(isr))
    state = "offline" if offline else "under_replicated" if missing else "healthy"
    return {
        "state": state,
        "offline": offline,
        "under_replicated": bool(missing),
        "offline_replicas": missing,
        "method": "leader and ISR membership",
        "confidence": 1.0,
    }
