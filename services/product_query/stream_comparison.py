from __future__ import annotations

from typing import Any

METRICS = (
    "throughput",
    "records_per_second",
    "bytes_per_second",
    "total_lag",
    "maximum_lag",
    "lag_velocity",
    "drain_time",
    "latency_p50",
    "latency_p95",
    "latency_p99",
    "offline_partitions",
    "under_replicated_partitions",
    "member_count",
)


def compare_samples(current: list[dict[str, Any]], baseline: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare measured samples; absent evidence is reported rather than synthesized as zero."""
    deltas: list[dict[str, Any]] = []
    missing: list[str] = []
    for metric in METRICS:
        left = [float(row[metric]) for row in baseline if isinstance(row.get(metric), (int, float))]
        right = [float(row[metric]) for row in current if isinstance(row.get(metric), (int, float))]
        if not left or not right:
            missing.append(metric)
            continue
        before, after = sum(left) / len(left), sum(right) / len(right)
        absolute = after - before
        deltas.append(
            {
                "metric": metric,
                "baseline": before,
                "current": after,
                "absolute_delta": absolute,
                "percentage_delta": (absolute / before * 100) if before else None,
            }
        )
    count = len(current) + len(baseline)
    return {
        "deltas": deltas,
        "sample_count": count,
        "confidence": min(1.0, count / 20) if deltas else None,
        "missing_evidence": missing,
    }
