from datetime import datetime, timedelta, timezone

from integrations.kafka_connect.redaction import redact_connector_config
from integrations.schema_registry.compatibility import classify_change
from packages.elastic_store.manifest import migrations
from packages.streaming.adapters.kafka import KafkaAdapter
from packages.streaming.adapters.kinesis import Adapter as KinesisAdapter
from packages.streaming.capabilities import CapabilityState
from packages.streaming.identity import stable_stream_id
from packages.streaming.redaction import safe_topic_config
from services.kafka_observer.offsets import OffsetSample, calculate_lag, drain_time, lag_velocity
from services.kafka_observer.partition_health import replication_health
from services.kafka_observer.retention import retention_risk


def test_forward_only_completion_migration_preserves_0009():
    plan = migrations()
    original = next(item for item in plan if item.migration_id == "0009_topic_queue_stream_360")
    completion = next(item for item in plan if item.migration_id == "0010_topic_queue_stream_360_completion")
    assert original.migration_id == "0009_topic_queue_stream_360"
    assert original.dependencies == ["0008_job_run_observability"]
    assert completion.migration_id == "0010_topic_queue_stream_360_completion"
    assert completion.dependencies == [original.migration_id]
    assert all(isinstance(item, dict) for item in completion.operations["transforms"])


def test_provider_capabilities_are_honest():
    assert KafkaAdapter().capabilities().state == CapabilityState.AVAILABLE
    assert KinesisAdapter().capabilities().state == CapabilityState.PARTIAL


def test_stable_ids_are_tenant_and_environment_scoped():
    first = stable_stream_id("a", "prod", "kafka", "c", "orders")
    assert first == stable_stream_id("a", "prod", "kafka", "c", "orders")
    assert first != stable_stream_id("b", "prod", "kafka", "c", "orders")


def test_lag_velocity_and_drain_time_are_explainable():
    now = datetime.now(timezone.utc)
    sample = OffsetSample(10, 100, 40, now)
    assert calculate_lag(sample)["lag_messages"] == 60
    velocity = lag_velocity([(now, 100), (now + timedelta(seconds=10), 80)])
    assert velocity["messages_per_second"] == -2
    assert drain_time(100, 20, 10)["seconds"] == 10
    assert drain_time(100, 10, 10)["state"] == "not_converging"


def test_missing_or_stale_offsets_are_not_zero():
    now = datetime.now(timezone.utc)
    assert calculate_lag(OffsetSample(0, 100, None, now))["lag_messages"] is None
    assert calculate_lag(OffsetSample(0, 100, 20, now, stale=True))["data_status"] == "stale"


def test_compacted_topic_is_not_given_delete_retention_math():
    result = retention_risk(
        cleanup_policy={"compact"},
        retention_seconds=100,
        oldest_unconsumed_age_seconds=90,
        log_start_offset=0,
        committed_offset=0,
    )
    assert result["state"] == "not_applicable"


def test_data_loss_candidate_and_replication_health():
    result = retention_risk(
        cleanup_policy={"delete"},
        retention_seconds=100,
        oldest_unconsumed_age_seconds=90,
        log_start_offset=20,
        committed_offset=10,
    )
    assert result["state"] == "data_loss_suspected"
    assert replication_health(replicas=[1, 2, 3], isr=[1, 2], leader_id=1)["state"] == "under_replicated"


def test_secret_config_is_dropped_not_masked():
    assert safe_topic_config({"retention.ms": "10", "sasl.jaas.config": "sentinel"}) == {"retention.ms": "10"}
    safe = redact_connector_config({"name": "x", "password": "sentinel", "connection.url": "jdbc://u:p@host"})
    assert safe == {"name": "x"}
    assert "sentinel" not in repr(safe)


def test_structural_schema_compatibility():
    result = classify_change("AVRO", {"fields": [{"name": "id", "type": "string"}]}, {"fields": []})
    assert result["classification"] == "breaking"
