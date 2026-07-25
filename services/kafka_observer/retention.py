from __future__ import annotations


def retention_risk(
    *,
    cleanup_policy: set[str],
    retention_seconds: float | None,
    oldest_unconsumed_age_seconds: float | None,
    log_start_offset: int | None,
    committed_offset: int | None,
) -> dict:
    evidence = {
        "kind": "estimated",
        "method": "oldest_unconsumed_age/retention",
        "inputs": {
            "retention_seconds": retention_seconds,
            "oldest_unconsumed_age_seconds": oldest_unconsumed_age_seconds,
            "log_start_offset": log_start_offset,
            "committed_offset": committed_offset,
        },
    }
    if "delete" not in cleanup_policy:
        return {
            "state": "not_applicable" if cleanup_policy == {"compact"} else "unknown",
            "time_remaining_seconds": None,
            "reasons": ["delete retention is not exclusively applicable"],
            "missing_inputs": [],
            "evidence": evidence,
        }
    missing = [
        n
        for n, v in (
            ("retention_seconds", retention_seconds),
            ("oldest_unconsumed_age_seconds", oldest_unconsumed_age_seconds),
        )
        if v is None
    ]
    if missing:
        return {
            "state": "unknown",
            "time_remaining_seconds": None,
            "reasons": ["insufficient retention evidence"],
            "missing_inputs": missing,
            "evidence": evidence,
        }
    assert retention_seconds is not None and oldest_unconsumed_age_seconds is not None
    remaining = retention_seconds - oldest_unconsumed_age_seconds
    if log_start_offset is not None and committed_offset is not None and committed_offset < log_start_offset:
        state = "data_loss_suspected"
    else:
        ratio = oldest_unconsumed_age_seconds / retention_seconds if retention_seconds > 0 else 1
        state = (
            "critical"
            if ratio >= 0.9
            else "high" if ratio >= 0.75 else "medium" if ratio >= 0.5 else "low" if ratio >= 0.25 else "none"
        )
    return {
        "state": state,
        "time_remaining_seconds": max(0, remaining),
        "reasons": [f"retention consumption ratio={oldest_unconsumed_age_seconds / retention_seconds:.2f}"],
        "missing_inputs": [],
        "evidence": evidence,
    }
