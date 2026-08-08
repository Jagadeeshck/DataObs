from __future__ import annotations

from services.monitoring.distribution_drift import jensen_shannon, population_stability_index

from .models import DriftThreshold


def compare_profiles(baseline: dict, branch: dict, thresholds: dict[str, DriftThreshold]) -> list[dict]:
    results = []
    for metric in ("row_count", "null_rate", "cardinality"):
        if metric not in baseline or metric not in branch:
            continue
        old, new = float(baseline[metric]), float(branch[metric])
        change = new - old
        score = abs(change) / max(abs(old), 1.0) if metric != "null_rate" else abs(change)
        results.append(_result(metric, old, new, change, score, thresholds[metric]))
    for metric, field in (("numerical_distribution", "histogram"), ("categorical_distribution", "categorical_top_k")):
        if field not in baseline or field not in branch:
            continue
        left, right = _aligned(baseline[field], branch[field])
        js, psi = jensen_shannon(left, right), population_stability_index(left, right)
        results.append(
            _result(
                metric,
                baseline[field],
                branch[field],
                None,
                max(js, min(1.0, psi)),
                thresholds[metric],
                {"jensen_shannon": js, "psi": psi},
            )
        )
    return results


def _aligned(left, right):
    if isinstance(left, dict):
        keys = sorted(set(left) | set(right))
        return [left.get(k, 0) for k in keys], [right.get(k, 0) for k in keys]
    if len(left) != len(right):
        raise ValueError("distribution profiles must have aligned buckets")
    return left, right


def _result(metric, old, new, absolute, score, threshold, extra=None):
    severity = "failed" if score >= threshold.fail else "warning" if score >= threshold.warning else "passed"
    return {
        "metric": metric,
        "baseline_value": old,
        "branch_value": new,
        "absolute_change": absolute,
        "relative_change": score,
        "drift_score": score,
        "threshold": {"warning": threshold.warning, "fail": threshold.fail},
        "status": severity,
        "severity": "high" if severity == "failed" else "medium" if severity == "warning" else "low",
        "confidence": 1.0,
        "reason_codes": [f"{metric}_{severity}"],
        **(extra or {}),
    }
