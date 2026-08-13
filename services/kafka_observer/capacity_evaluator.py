"""Capacity evaluation stage for the existing Stream Intelligence worker."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from packages.streaming.capacity import (
    CapacityBottleneck,
    CapacityDimension,
    CapacityDimensionName,
    CapacityEvaluation,
    CapacityLimit,
    CapacityMeasurement,
    CapacityPlanningPolicy,
    CapacityState,
    RetentionCapacityPlan,
    SaturationSignal,
    calculate_headroom,
    evaluate_consumer_capacity,
    evaluate_parallelism,
)

STRONG_SIGNALS = frozenset({"provider_throttling", "quota_breach", "capacity_rejection", "provisioned_capacity_exhausted"})


def evaluate_capacity(evidence: dict[str, Any], policy: CapacityPlanningPolicy | None = None) -> CapacityEvaluation:
    """Evaluate one normalized, bounded evidence bundle without provider calls.

    The adapters own normalization. In particular, SQS supplies backlog rather
    than lag, and Kinesis on-demand supplies no invented fixed limit.
    """
    policy = policy or CapacityPlanningPolicy()
    now = evidence.get("evaluated_at") or datetime.now(timezone.utc)
    system = evidence.get("messaging_system", "unknown")
    demand: CapacityMeasurement | None = evidence.get("demand")
    limit: CapacityLimit | None = evidence.get("limit")
    if system == "kinesis" and evidence.get("stream_mode") == "on_demand":
        limit = None
    headroom = calculate_headroom(demand, limit)
    utilisation = headroom.utilisation
    state = CapacityState.INSUFFICIENT_DATA
    reasons = list(headroom.reason_codes)
    if utilisation is not None:
        state = CapacityState.CONSTRAINED if utilisation >= policy.constrained_utilisation else CapacityState.WATCH if utilisation >= policy.watch_utilisation else CapacityState.HEALTHY

    signals: list[SaturationSignal] = []
    for raw in evidence.get("signals", ()):
        signal_type = raw["signal_type"]
        strong = signal_type in STRONG_SIGNALS
        strength = "authoritative" if strong and raw.get("authoritative") else "strong" if strong else "supporting"
        signals.append(SaturationSignal(signal_type, CapacityDimensionName(raw.get("dimension", CapacityDimensionName.BACKLOG.value)), raw.get("observed_value"), raw.get("threshold_or_limit"), raw.get("unit"), strength, raw.get("method", "provider_measured"), raw.get("first_observed_at", now), raw.get("last_observed_at", now), raw.get("confidence", 0.5), tuple(raw.get("evidence_refs", ()))))
    strong = [signal for signal in signals if signal.strength in {"authoritative", "strong"}]
    if any(signal.signal_type == "provider_throttling" for signal in strong):
        state = CapacityState.THROTTLED
    elif strong:
        state = CapacityState.SATURATED

    refs = tuple(dict.fromkeys(([demand.evidence_ref] if demand else []) + ([limit.evidence_ref] if limit else []) + list(evidence.get("evidence_refs", ()))))
    dimension = CapacityDimension(CapacityDimensionName.PROVIDER_INGRESS, demand.value if demand else None, limit.value if limit else None, utilisation, headroom.absolute, state, demand.method.value if demand else "unavailable", min(demand is not None and 1.0 or 0.0, limit.confidence if limit else 1.0), evidence.get("source_coverage", 0.0), tuple(code.removesuffix("_missing") for code in reasons), tuple(reasons), refs)
    consumer = evaluate_consumer_capacity(evidence.get("arrival_rate"), evidence.get("processing_rate"), evidence.get("backlog"))
    parallelism = evaluate_parallelism(system, evidence.get("consumer_count"), evidence.get("partition_count"))
    candidates: list[CapacityBottleneck] = []
    if consumer.capacity_deficit and consumer.capacity_deficit > 0:
        candidates.append(CapacityBottleneck("consumer_processing", 0.8, ("processing_below_arrival",), refs))
    if parallelism.ceiling_reached:
        candidates.append(CapacityBottleneck("consumer_parallelism", 0.8, ("parallelism_ceiling_reached",), refs))
    if strong:
        candidates.append(CapacityBottleneck("provider_ingress", max(item.confidence for item in strong), ("strong_saturation_evidence",), refs))
    retention = evidence.get("retention_forecast")
    retention_plan = RetentionCapacityPlan(retention, evidence.get("earliest_exhaustion_seconds"), retention.confidence, retention.data_coverage) if retention else None
    missing = tuple(dict.fromkeys(reasons + (["checkpoints"] if system == "azure_event_hubs" and evidence.get("checkpoint_missing") else [])))
    confidence = min(1.0, evidence.get("source_coverage", 0.0) * (0.7 if demand and demand.method.value == "provider_approximate" else 1.0))
    return CapacityEvaluation(state, (dimension,), tuple(signals), consumer, parallelism, evidence.get("partition_shard_pressure"), retention_plan, tuple(candidates or [CapacityBottleneck("unknown", confidence, ("no_bottleneck_evidence",), refs)]), confidence, missing, refs)


def evaluation_document(evaluation: CapacityEvaluation, scope: dict[str, str], evaluation_id: str, fencing_token: int) -> dict[str, Any]:
    """Create the durable document appended before its OCC projection."""
    return asdict(evaluation) | scope | {"evaluation_id": evaluation_id, "fencing_token": fencing_token, "evaluated_at": datetime.now(timezone.utc).isoformat(), "schema_version": "v1"}
