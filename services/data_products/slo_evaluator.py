from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256

from packages.domain_model.data_product import DataProductSLODefinition, DataProductSLOEvaluation
from packages.domain_model.slo import DataReliabilitySLOEvaluation


def roll_up_child_slos(
    children: list[tuple[DataReliabilitySLOEvaluation, float, bool]],
) -> dict[str, object]:
    """Aggregate canonical child evaluations without re-reading raw evidence.

    Duplicate evaluation IDs are counted once. Unknown/partial children do not
    enter the weighted value, and a failed critical child caps the result state.
    """
    unique: dict[str, tuple[DataReliabilitySLOEvaluation, float, bool]] = {}
    for child, weight, critical in children:
        if weight < 0:
            raise ValueError("child SLO weight cannot be negative")
        unique.setdefault(child.id, (child, weight, critical))
    observed = [
        item
        for item in unique.values()
        if item[0].sli_actual is not None and item[0].state not in ("unknown", "partial")
    ]
    denominator = sum(weight for _, weight, _ in observed)
    actual = sum(child.sli_actual * weight for child, weight, _ in observed) / denominator if denominator else None
    critical_failed = any(
        critical and child.state in ("critical", "exhausted") for child, _, critical in unique.values()
    )
    state = "unknown" if actual is None else ("failed" if critical_failed else "passed")
    return {
        "actual_value": actual,
        "state": state,
        "critical_component_cap_applied": critical_failed,
        "component_evaluation_ids": sorted(unique),
        "missing_component_ids": sorted(
            child.slo_id for child, _, _ in unique.values() if child.state in ("unknown", "partial")
        ),
        "formula": "deduplicated weighted mean of observed canonical child SLO evaluations",
    }


def evaluate_slo(
    definition: DataProductSLODefinition,
    *,
    window_start: datetime,
    window_end: datetime,
    actual_value: float | None,
    denominator: float,
    evidence_refs: list[str],
    stale: bool = False,
    now: datetime | None = None,
) -> DataProductSLOEvaluation:
    now = now or datetime.now(timezone.utc)
    if window_start >= window_end or window_end > now:
        raise ValueError("SLO evaluation window is invalid or uses future data")
    missing = [] if evidence_refs else ["source_monitor_evidence"]
    if stale:
        state = "stale"
    elif not evidence_refs:
        state = "source_unavailable"
    elif denominator <= 0 or actual_value is None:
        state = "insufficient_data"
    else:
        state = "passed" if actual_value >= definition.objective else "failed"
    evidence_fingerprint = sha256(json.dumps(sorted(set(evidence_refs)), separators=(",", ":")).encode()).hexdigest()
    material = "\0".join(
        (
            "v2",
            definition.tenant_id,
            definition.environment,
            definition.product_id,
            definition.id,
            str(definition.revision),
            window_start.isoformat(),
            window_end.isoformat(),
            definition.evaluation_method,
            evidence_fingerprint,
        )
    )
    return DataProductSLOEvaluation(
        id=sha256(material.encode()).hexdigest(),
        tenant_id=definition.tenant_id,
        environment=definition.environment,
        product_id=definition.product_id,
        slo_id=definition.id,
        definition_revision=definition.revision,
        window_start=window_start,
        window_end=window_end,
        objective=definition.objective,
        actual_value=actual_value,
        denominator=denominator,
        source_monitor_ids=definition.source_monitor_ids,
        source_evaluation_refs=sorted(set(evidence_refs)),
        coverage=1 if evidence_refs else 0,
        confidence=1 if evidence_refs and denominator > 0 and not stale else 0,
        missing_evidence=missing,
        state=state,
        evaluated_at=now,
    )
