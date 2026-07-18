from integrations.kafka.changes import diff
from packages.pathways.identity import cluster_id, edge_id
from packages.pathways.lag import estimate_lag
from packages.pathways.retention_risk import calculate_retention_risk
from packages.pathways.span_normalizer import normalize_span
from services.kafka_observer.collector_registry import CapabilityBinding, validate_bindings
from services.pathway_worker.aggregator import aggregate


def test_deterministic_ids_are_normalized():
    assert cluster_id("Tenant", "PROD", "i", "cluster") == cluster_id(" tenant ", "prod", "I", "CLUSTER")
    assert edge_id("t", "e", "a", "b", "kafka") != edge_id("t", "e", "b", "a", "kafka")


def test_old_and_new_span_conventions_and_key_protection():
    old = normalize_span(
        {
            "messaging": {
                "operation": "receive",
                "destination": "orders",
                "kafka": {"consumer": {"group": "g"}, "message": {"key": "secret"}},
            },
            "trace": {"id": "abc"},
        }
    )
    new = normalize_span(
        {
            "messaging": {
                "operation": {"type": "receive"},
                "destination": {"name": "orders"},
                "consumer": {"group": {"name": "g"}},
            }
        }
    )
    assert old["messaging.destination.name"] == new["messaging.destination.name"] == "orders"
    assert old["messaging.kafka.message.key"] != "secret"


def test_lag_methods_and_negative_anomaly():
    assert estimate_lag(10, 20, consume_rate=1)["lag_messages"] == 0
    assert estimate_lag(100, 50, consume_rate=10) == {
        "lag_messages": 50,
        "lag_seconds": 5.0,
        "method": "consume_rate",
        "confidence": 0.75,
    }
    assert estimate_lag(100, None)["method"] == "unknown"


def test_retention_risk_is_explainable():
    risk = calculate_retention_risk(
        lag=100,
        retention_seconds=100,
        retention_bytes=1000,
        partition_bytes=1000,
        average_message_bytes=10,
        produce_rate=2,
        consume_rate=1,
        backlog_age_seconds=95,
    )
    assert risk["state"] == "data_loss_likely"
    assert len(risk["reasons"]) == 2


def test_capability_provider_conflicts_rejected():
    common = dict(
        capability="broker_metrics",
        collection_interval_seconds=30,
        source_integration_id="i",
        source_event_identity="event",
        deduplication_key="key",
    )
    bindings = [
        CapabilityBinding(selected_provider="edot", **common),
        CapabilityBinding(selected_provider="elastic_agent", **common),
    ]
    try:
        validate_bindings(bindings)
    except ValueError as error:
        assert "conflicting authoritative providers" in str(error)
    else:
        raise AssertionError("conflict accepted")
    validate_bindings(bindings, comparison_mode=True)


def test_percentile_aggregation():
    result = aggregate([1, 2, 3, 4], [10, 20, 30, 40], 2)
    assert result["p50_latency_ms"] == 2.5
    assert result["throughput_messages_per_second"] == 2


def test_connector_secrets_redacted_from_diff():
    result = diff({"password": "old"}, {"password": "new", "tasks.max": "2"})
    assert "password" not in result
    assert result["tasks.max"]["after"] == "2"
