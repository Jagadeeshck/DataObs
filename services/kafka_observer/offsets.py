from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median


@dataclass(frozen=True)
class OffsetSample:
    log_start_offset: int | None
    high_watermark: int | None
    committed_offset: int | None
    observed_at: datetime
    stale: bool = False


def calculate_lag(sample: OffsetSample) -> dict:
    missing = [name for name in ("high_watermark", "committed_offset") if getattr(sample, name) is None]
    if sample.stale:
        return {"lag_messages": None, "data_status": "stale", "method": "offset_difference", "missing_inputs": missing}
    if missing:
        return {
            "lag_messages": None,
            "data_status": "partial",
            "method": "offset_difference",
            "missing_inputs": missing,
        }
    assert sample.high_watermark is not None and sample.committed_offset is not None
    if sample.committed_offset < 0:
        return {
            "lag_messages": None,
            "data_status": "unknown",
            "method": "offset_difference",
            "missing_inputs": ["valid_committed_offset"],
        }
    return {
        "lag_messages": max(sample.high_watermark - sample.committed_offset, 0),
        "data_status": "complete",
        "method": "max(high_watermark-committed_offset,0)",
        "missing_inputs": [],
    }


def lag_velocity(samples: list[tuple[datetime, int]]) -> dict:
    ordered = sorted(set(samples))
    if len(ordered) < 2:
        return {"messages_per_second": None, "sample_count": len(ordered), "confidence": 0.0, "trend": "unknown"}
    elapsed = (ordered[-1][0] - ordered[0][0]).total_seconds()
    if elapsed <= 0:
        return {"messages_per_second": None, "sample_count": len(ordered), "confidence": 0.0, "trend": "unknown"}
    # The median of all pairwise slopes is bounded and resistant to isolated
    # collection spikes (Theil-Sen without materialising regression matrices).
    slopes = [
        (right[1] - left[1]) / seconds
        for index, left in enumerate(ordered)
        for right in ordered[index + 1 :]
        if (seconds := (right[0] - left[0]).total_seconds()) > 0
    ]
    if not slopes:
        return {"messages_per_second": None, "sample_count": len(ordered), "confidence": 0.0, "trend": "unknown"}
    rate = median(slopes)
    return {
        "messages_per_second": rate,
        "sample_count": len(ordered),
        "interval_seconds": elapsed,
        "confidence": min(0.95, 0.4 + len(ordered) / 20),
        "method": "median_pairwise_slope",
        "outlier_treatment": "median",
        "trend": "growing" if rate > 0 else "reducing" if rate < 0 else "stable",
    }


def drain_time(lag: int | None, consume_rate: float | None, produce_rate: float | None) -> dict:
    missing = [
        n for n, v in (("lag", lag), ("consume_rate", consume_rate), ("produce_rate", produce_rate)) if v is None
    ]
    if missing:
        return {
            "state": "unknown",
            "seconds": None,
            "method": "lag/(consume_rate-produce_rate)",
            "missing_inputs": missing,
            "confidence": 0.0,
        }
    assert lag is not None and consume_rate is not None and produce_rate is not None
    net = consume_rate - produce_rate
    if net <= 0:
        return {
            "state": "not_converging",
            "seconds": None,
            "net_drain_rate": net,
            "method": "lag/(consume_rate-produce_rate)",
            "missing_inputs": [],
            "confidence": 0.8,
        }
    return {
        "state": "converging",
        "seconds": round(lag / net),
        "net_drain_rate": net,
        "method": "lag/(consume_rate-produce_rate)",
        "missing_inputs": [],
        "confidence": 0.8,
    }
