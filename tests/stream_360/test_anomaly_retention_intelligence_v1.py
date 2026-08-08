from datetime import datetime, timedelta, timezone

from packages.elastic_store.manifest import migrations
from packages.streaming.intelligence import (
    DetectorDefinition,
    DetectorPreviousState,
    DetectorState,
    EvidenceSeries,
    ForecastState,
    TimeSeriesPoint,
    classify_failure_candidate,
    evaluate_anomaly,
    partition_skew,
    relative_change,
    retention_forecast,
    robust_baseline,
    safe_error_fingerprint,
)
from services.kafka_observer.change_overlays import correlate_change

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def definition(**changes):
    values = dict(
        detector_id="d",
        tenant_id="t",
        environment="prod",
        resource_type="consumer_group",
        resource_id="g",
        metric="total_lag",
        method="robust_zscore",
        direction="high",
        baseline_window_seconds=3600,
        evaluation_window_seconds=60,
        evaluation_interval_seconds=60,
        minimum_sample_count=3,
        enabled=True,
    )
    values.update(changes)
    return DetectorDefinition(**values)


def series(values):
    return EvidenceSeries(
        tuple(TimeSeriesPoint(NOW + timedelta(minutes=i), value) for i, value in enumerate(values)),
        len(values),
        "offset_history",
    )


def test_migration_is_forward_only_after_reliability_closure():
    migration = migrations()[-1]
    assert migration.migration_id == "0026_stream_anomaly_retention_intelligence"
    assert migration.dependencies == ["0025_stream_pathway_reliability_production_closure"]


def test_zero_constant_baseline_and_repeated_spike_are_explainable():
    baseline = robust_baseline(series([0, 0, 0]))
    assert baseline.median == baseline.mad == 0
    first = evaluate_anomaly(definition(), series([0, 0, 0, 5]))
    assert first.state == DetectorState.WATCH
    assert "constant_baseline_change" in first.reason_codes
    second = evaluate_anomaly(definition(), series([0, 0, 0, 5]), DetectorPreviousState(first.state, 1, 0))
    assert second.state == DetectorState.ANOMALOUS


def test_missing_is_not_zero_and_insufficient_is_not_normal():
    points = series([0, 0]).points + (TimeSeriesPoint(NOW + timedelta(minutes=2), None, "missing"),)
    result = evaluate_anomaly(definition(), EvidenceSeries(points, 3, "offset_history"))
    assert result.state == DetectorState.INSUFFICIENT_DATA
    assert result.observed_value is None


def test_relative_change_has_explicit_zero_policy():
    assert relative_change(5, 0) == (5, "zero_baseline_absolute_change")


def test_partition_zero_and_single_partition_semantics():
    result = partition_skew({0: 1, 1: 1, 2: 100}, 3, threshold=3)
    assert result.affected_partition_ids == (2,)
    assert partition_skew({0: 10}, 1).affected_partition_ids == ()


def test_drain_and_retention_forecast_do_not_predict_false_loss():
    draining = retention_forecast(
        current_lag=100, production_rates=[10, 10, 10], consumption_rates=[20, 20, 20], horizon_seconds=3600
    )
    assert draining.estimated_drain_time_seconds == 10
    assert draining.state != ForecastState.DATA_LOSS_SUSPECTED
    stalled = retention_forecast(current_lag=100, production_rates=[10], consumption_rates=[10], horizon_seconds=3600)
    assert stalled.state == ForecastState.NOT_DRAINING
    assert stalled.estimated_drain_time_seconds is None


def test_metadata_only_candidate_and_noncausal_overlay():
    candidate = classify_failure_candidate(
        tenant_id="t",
        environment="prod",
        resource_type="consumer_group",
        resource_id="g",
        observed_at=NOW,
        retry_rate=2,
        dlq_growth=1,
        classifications=["Schema_Mismatch"],
    )
    assert candidate and candidate.classification == "poison_message_candidate"
    assert len(safe_error_fingerprint(["Schema_Mismatch"])) == 24
    assert "Schema_Mismatch" not in repr(candidate)
    overlay = correlate_change(
        anomaly_at=NOW,
        changed_at=NOW - timedelta(minutes=1),
        change_type="schema_version_change",
        changed_resource="schema:orders",
        summary="version 4 installed",
        source="schema_history",
        evidence_reference="e:1",
    )
    assert overlay and overlay.summary.startswith("change observed near anomaly")
    assert "caused by" not in overlay.summary
