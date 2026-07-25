"""Evidence-based, approval-gated monitor recommendations."""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Iterable

from packages.domain_model.monitor import MonitorRecommendation, MonitorTarget, MonitorType

from .heuristics import recommend_types


class InvalidRecommendationTransition(ValueError):
    pass


TRANSITIONS = {
    "proposed": {"accepted", "rejected", "deferred", "expired"},
    "accepted": {"applied", "superseded"},
    "deferred": {"proposed", "expired"},
    "applied": {"superseded"},
}


def transition(recommendation: MonitorRecommendation, state: str) -> MonitorRecommendation:
    if state not in TRANSITIONS.get(recommendation.state, set()):
        raise InvalidRecommendationTransition(f"{recommendation.state} -> {state} is not allowed")
    return recommendation.model_copy(update={"state": state})


def generate(
    tenant_id: str, asset_id: str, metadata: dict[str, Any], existing: Iterable[tuple[str, str]] = ()
) -> list[MonitorRecommendation]:
    duplicates = set(existing)
    output: list[MonitorRecommendation] = []
    for monitor_type, rationale in recommend_types(metadata):
        if (asset_id, monitor_type) in duplicates:
            continue
        digest = hashlib.sha256(f"{tenant_id}|{asset_id}|{monitor_type}".encode()).hexdigest()[:24]
        output.append(
            MonitorRecommendation(
                id=f"rec-{digest}",
                tenant_id=tenant_id,
                monitor_type=MonitorType(monitor_type),
                target=MonitorTarget(asset_id=asset_id),
                rationale=rationale,
                evidence=[{"type": "asset_metadata", "ref": f"asset:{asset_id}", "redacted": True}],
                expected_compute_cost="low",
                expected_collection_permissions=["aggregate:read"],
                confidence=0.8 if metadata else 0.4,
                business_priority=str(metadata.get("criticality", "medium")),
                duplication_analysis="no enabled monitor with the same target and category",
                coverage_gap_closed=[monitor_type],
                risk="requires source query budget and explicit acceptance",
            )
        )
    return output


def accept(
    recommendation: MonitorRecommendation,
    create_monitor: Callable[[MonitorRecommendation, str], Any],
    idempotency_key: str,
) -> Any:
    if recommendation.state not in {"proposed", "accepted"}:
        raise InvalidRecommendationTransition("only proposed recommendations can be accepted")
    # Persistence owns idempotency; the service never mutates a monitor directly.
    return create_monitor(recommendation.model_copy(update={"state": "accepted"}), idempotency_key)
