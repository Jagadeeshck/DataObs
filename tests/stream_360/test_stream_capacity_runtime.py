from datetime import datetime, timezone

import pytest

from packages.streaming.capacity import (
    CapacityLimit,
    CapacityMeasurement,
    LimitSourceType,
    calculate_headroom,
    evaluate_consumer_capacity,
    evaluate_parallelism,
)
from packages.streaming.contracts import MeasurementMethod
from services.kafka_observer.capacity_evaluator import evaluate_capacity

NOW = datetime.now(timezone.utc)


def measurement(value=50, unit="messages/s", method=MeasurementMethod.PROVIDER_MEASURED):
    return CapacityMeasurement(value, unit, method, NOW, "metric:1")


def limit(value=100, unit="messages/s"):
    return CapacityLimit(
        value, unit, "stream", "quota", LimitSourceType.PROVIDER_QUOTA_API, True, 1, "aws", "kinesis", "quota:1"
    )


def test_headroom_known_missing_zero_and_unit_safety():
    assert calculate_headroom(measurement(), limit()).ratio == 0.5
    assert calculate_headroom(measurement(0), limit()).utilisation == 0
    assert calculate_headroom(measurement(), None).absolute is None
    assert calculate_headroom(measurement(unit="bytes/s"), limit()).reason_codes == ("unit_mismatch",)
    with pytest.raises(ValueError):
        limit(0)


def test_consumer_convergence_and_not_draining():
    converging = evaluate_consumer_capacity(5, 10, 100)
    assert converging.convergence == "converging" and converging.estimated_drain_time == 20
    diverging = evaluate_consumer_capacity(10, 5, 100)
    assert (
        diverging.state == "not_draining" and diverging.estimated_drain_time is None and diverging.capacity_deficit == 5
    )
    assert evaluate_consumer_capacity(10, 10, 1).convergence == "stable"


def test_pressure_is_not_saturation_and_throttling_is():
    pressure = evaluate_capacity(
        {
            "provider": "aws",
            "messaging_system": "sqs",
            "arrival_rate": 10,
            "processing_rate": 5,
            "backlog": 100,
            "signals": [{"signal_type": "backlog_growth"}],
            "source_coverage": 1,
        }
    )
    assert pressure.overall_state == "insufficient_data"
    assert pressure.saturation_signals[0].strength == "supporting"
    throttled = evaluate_capacity(
        {
            "provider": "aws",
            "messaging_system": "kinesis",
            "stream_mode": "provisioned",
            "demand": measurement(),
            "limit": limit(),
            "signals": [{"signal_type": "provider_throttling", "authoritative": True}],
            "source_coverage": 1,
        }
    )
    assert throttled.overall_state == "throttled"


def test_kinesis_on_demand_and_kafka_parallelism_semantics():
    result = evaluate_capacity(
        {
            "provider": "aws",
            "messaging_system": "kinesis",
            "stream_mode": "on_demand",
            "demand": measurement(),
            "limit": limit(),
            "source_coverage": 1,
        }
    )
    assert result.dimensions[0].known_limit is None and result.dimensions[0].utilisation is None
    assert evaluate_parallelism("kafka", 12, 12).state == "parallelism_ceiling_reached"
    assert evaluate_parallelism("sqs", 12, None).state == "not_applicable"


def test_approximate_measurement_reduces_confidence_and_missing_checkpoint_is_not_zero():
    sqs = evaluate_capacity(
        {
            "provider": "aws",
            "messaging_system": "sqs",
            "demand": measurement(method=MeasurementMethod.PROVIDER_APPROXIMATE),
            "limit": limit(),
            "source_coverage": 1,
        }
    )
    assert sqs.confidence == 0.7
    hubs = evaluate_capacity(
        {
            "provider": "azure",
            "messaging_system": "azure_event_hubs",
            "checkpoint_missing": True,
            "source_coverage": 0.5,
        }
    )
    assert "checkpoints" in hubs.missing_inputs and hubs.consumer_capacity.arrival_rate is None
