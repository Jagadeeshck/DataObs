"""Explainable fixed/learned/hybrid decisions."""

from __future__ import annotations

from typing import Any


def evaluate(
    definition,
    observation,
    baseline: dict[str, Any] | None = None,
    *,
    suppressed: bool = False,
    provider_status: str = "supported",
) -> dict[str, Any]:
    reasons: list[str] = []
    if provider_status in {"temporarily_unavailable", "not_configured", "permission_limited", "unsupported"}:
        state = "source_unavailable"
        reasons.append(f"provider_{provider_status}")
    elif observation.missing_data or observation.value is None:
        state = "insufficient_data"
        reasons.append("missing_observation")
    else:
        low, high = definition.threshold.minimum, definition.threshold.maximum
        mature = baseline and baseline.get("cold_start_state") == "mature"
        if baseline is not None and mature and definition.threshold.mode.value in {"learned", "hybrid"}:
            low = baseline.get("expected_minimum") if low is None else low
            high = baseline.get("expected_maximum") if high is None else high
        breached = (low is not None and observation.value < low) or (high is not None and observation.value > high)
        state = "breached" if breached else "passed"
        reasons.append(
            "below_minimum"
            if low is not None and observation.value < low
            else "above_maximum" if high is not None and observation.value > high else "within_threshold"
        )
    if suppressed and state == "breached":
        state = "suppressed"
        reasons.append("active_suppression")
    return {
        "state": state,
        "reason_codes": reasons,
        "definition_revision": definition.revision,
        "baseline_version": baseline.get("baseline_version") if baseline else None,
        "fixed_threshold": definition.threshold.model_dump(mode="json"),
        "learned_threshold": (
            {"minimum": baseline.get("expected_minimum"), "maximum": baseline.get("expected_maximum")}
            if baseline
            else None
        ),
        "missing_inputs": [] if state not in {"insufficient_data", "source_unavailable"} else reasons,
    }
