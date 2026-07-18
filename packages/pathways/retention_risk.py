from __future__ import annotations


def calculate_retention_risk(
    *,
    lag: int,
    retention_seconds: float | None,
    retention_bytes: int | None,
    partition_bytes: int | None,
    average_message_bytes: float | None,
    produce_rate: float,
    consume_rate: float,
    backlog_age_seconds: float | None = None,
) -> dict:
    time_ratio = (
        backlog_age_seconds / retention_seconds if backlog_age_seconds is not None and retention_seconds else None
    )
    backlog_bytes = lag * average_message_bytes if average_message_bytes is not None else None
    bytes_ratio = backlog_bytes / retention_bytes if backlog_bytes is not None and retention_bytes else None
    drain_rate = consume_rate - produce_rate
    drain_time = lag / drain_rate if drain_rate > 0 else None
    ratio = max([r for r in (time_ratio, bytes_ratio) if r is not None], default=None)
    if ratio is None:
        state = "unknown"
    elif ratio >= 1:
        state = "data_loss_likely"
    elif ratio >= 0.9:
        state = "critical"
    elif ratio >= 0.75:
        state = "warning"
    elif ratio >= 0.5:
        state = "watch"
    else:
        state = "healthy"
    reasons = [f"time retention risk ratio={time_ratio:.3f}"] if time_ratio is not None else []
    if bytes_ratio is not None:
        reasons.append(f"bytes retention risk ratio={bytes_ratio:.3f}")
    if ratio is None:
        reasons.append("insufficient retention inputs")
    return {
        "state": state,
        "time_risk_ratio": time_ratio,
        "bytes_risk_ratio": bytes_ratio,
        "drain_time_seconds": drain_time,
        "estimated_data_loss_seconds": (
            max(0, retention_seconds - backlog_age_seconds)
            if retention_seconds and backlog_age_seconds is not None
            else None
        ),
        "reasons": reasons,
        "inputs": {
            "lag": lag,
            "retention_seconds": retention_seconds,
            "retention_bytes": retention_bytes,
            "partition_bytes": partition_bytes,
            "produce_rate": produce_rate,
            "consume_rate": consume_rate,
        },
    }
