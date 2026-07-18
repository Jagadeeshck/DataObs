from __future__ import annotations


def estimate_lag(
    latest_offset: int,
    committed_offset: int | None,
    *,
    unread_age_seconds: float | None = None,
    consume_rate: float | None = None,
    produce_rate: float | None = None,
) -> dict:
    if committed_offset is None:
        return {
            "lag_messages": None,
            "lag_seconds": None,
            "method": "unknown",
            "confidence": 0.0,
            "reason": "no committed offset",
        }
    lag = max(0, latest_offset - committed_offset)
    if unread_age_seconds is not None:
        return {
            "lag_messages": lag,
            "lag_seconds": max(0, unread_age_seconds),
            "method": "next_unread_timestamp",
            "confidence": 0.95,
        }
    if consume_rate and consume_rate > 0:
        return {"lag_messages": lag, "lag_seconds": lag / consume_rate, "method": "consume_rate", "confidence": 0.75}
    if produce_rate and produce_rate > 0:
        return {"lag_messages": lag, "lag_seconds": lag / produce_rate, "method": "produce_rate", "confidence": 0.45}
    return {"lag_messages": lag, "lag_seconds": None, "method": "unknown", "confidence": 0.0}
