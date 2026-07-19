from statistics import median


def detect(tasks, threshold=3.0):
    durations = sorted(x.get("duration_ms", 0) for x in tasks)
    n = len(durations)
    if n < 5:
        return {
            "skew": False,
            "method": "duration and volume ratios",
            "samples": n,
            "confidence": 0,
            "reason": "insufficient samples",
        }
    med = median(durations)
    p95 = durations[min(n - 1, int((n - 1) * 0.95))]
    maximum = durations[-1]
    ratio = maximum / med if med else None
    p95_ratio = p95 / med if med else None
    stragglers = sum(1 for x in durations if med and x / med >= threshold)
    return {
        "skew": bool(ratio and ratio >= threshold and stragglers > 0),
        "method": "max/median plus straggler count",
        "threshold": threshold,
        "max_median_ratio": ratio,
        "p95_median_ratio": p95_ratio,
        "straggler_count": stragglers,
        "samples": n,
        "confidence": min(1, n / 100),
    }
