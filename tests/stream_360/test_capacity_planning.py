from copy import deepcopy

import pytest

from packages.streaming.capacity import capacity_recommendations, recovery_capacity, simulate_capacity


def snapshot(system="kafka"):
    return {
        "messaging_system": system,
        "confidence": 0.8,
        "evidence_refs": ["metric:arrival", "metric:processing"],
        "consumer_capacity": {"arrival_rate": 1000, "processing_rate": 1200, "capacity_deficit": 0},
        "backlog": 360000,
        "partition_shard_pressure": {"hot_ids": ["3"]},
    }


def test_recovery_capacity_is_derived_required_capacity():
    result = recovery_capacity(1000, 360000, 1200, 600)
    assert result.required_processing_rate == 1600
    assert result.additional_processing_rate_required == 400
    assert result.method == "derived_required_capacity"


def test_recommendations_are_advisory_and_provider_aware():
    kafka = capacity_recommendations(snapshot())
    assert {item.recommendation_type for item in kafka} == {"investigate_hot_partition", "rebalance_partition_keys"}
    assert all(item.reason_codes and item.evidence_refs and item.prerequisites and item.limitations for item in kafka)
    assert all(item.advisory_only and not item.automatic_execution and item.requires_human_review for item in kafka)
    assert "human approval required" in kafka[1].prerequisites
    sqs = capacity_recommendations(snapshot("sqs"))
    assert not {"rebalance_partition_keys", "investigate_hot_partition"} & {item.recommendation_type for item in sqs}


def test_scenario_is_bounded_stateless_and_not_observed():
    current = snapshot()
    before = deepcopy(current)
    scenario = simulate_capacity(
        current, traffic_multiplier=1.5, consumer_processing_multiplier=2, recovery_target_seconds=600
    )
    assert current == before
    assert scenario["hypothetical"] is True and scenario["observation_status"] == "not_observed"
    assert scenario["persisted"] is False and scenario["arrival_rate"] == 1500
    with pytest.raises(ValueError):
        simulate_capacity(current, traffic_multiplier=10.1)


def test_kafka_parallelism_advice_does_not_claim_throughput_multiplier():
    full = snapshot()
    full["parallelism"] = {"consumer_count": 12, "assignable_partitions": 12, "ceiling_reached": True}
    assert "increase_consumer_parallelism" not in {r.recommendation_type for r in capacity_recommendations(full)}
