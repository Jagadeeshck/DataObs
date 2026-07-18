from __future__ import annotations

import math


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def aggregate(latencies_ms: list[float], sizes_bytes: list[int], duration_seconds: float) -> dict:
    return {
        "p50_latency_ms": percentile(latencies_ms, 0.5),
        "p95_latency_ms": percentile(latencies_ms, 0.95),
        "p99_latency_ms": percentile(latencies_ms, 0.99),
        "payload_size_p50_bytes": percentile([float(x) for x in sizes_bytes], 0.5),
        "payload_size_p95_bytes": percentile([float(x) for x in sizes_bytes], 0.95),
        "throughput_messages_per_second": len(latencies_ms) / duration_seconds if duration_seconds > 0 else 0,
        "throughput_bytes_per_second": sum(sizes_bytes) / duration_seconds if duration_seconds > 0 else 0,
        "sample_count": len(latencies_ms),
    }
