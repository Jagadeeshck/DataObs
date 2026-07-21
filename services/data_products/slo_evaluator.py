from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from packages.domain_model.data_product import DataProductSLODefinition, DataProductSLOEvaluation


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
    material = f"{definition.id}:{definition.revision}:{window_start.isoformat()}:{window_end.isoformat()}"
    return DataProductSLOEvaluation(
        id=sha256(material.encode()).hexdigest(),
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
