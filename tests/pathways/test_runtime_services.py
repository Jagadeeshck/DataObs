from integrations.kafka.config import KafkaObserverConfig
from services.kafka_observer.checkpoint_store import MemoryCheckpointStore
from services.kafka_observer.collector_registry import CapabilityBinding
from services.kafka_observer.repository import MemoryObserverRepository
from services.kafka_observer.service import KafkaObserverService


class Admin:
    def inventory(self):
        return {"cluster_id": "c", "brokers": [], "topics": [], "consumer_groups": []}


def test_observer_persists_collection_through_repository():
    repository = MemoryObserverRepository()
    binding = CapabilityBinding(
        capability="offset_inventory",
        selected_provider="kafka_admin",
        collection_interval_seconds=30,
        source_integration_id="i",
        source_event_identity="e",
        deduplication_key="d",
    )
    result = KafkaObserverService(Admin(), MemoryCheckpointStore(), [binding], repository=repository).collect_once()
    assert repository.collections == [result["inventory"]]
    assert repository.load_checkpoint("dataobs_kafka_observer")["cluster_id"] == "c"


def test_plaintext_rejected_by_cli_configuration_outside_development(tmp_path):
    from services.kafka_observer.cli import _load

    path = tmp_path / "observer.yaml"
    path.write_text(
        "tenant_id: t\nenvironment: production\nintegration_id: i\nbootstrap_servers: [k:9092]\nsecurity:\n  protocol: PLAINTEXT\n"
    )
    try:
        _load(str(path))
    except ValueError as error:
        assert "only in development" in str(error)
    else:
        raise AssertionError("production plaintext accepted")


def test_config_forbids_unknown_fields():
    try:
        KafkaObserverConfig(
            tenant_id="t", environment="dev", integration_id="i", bootstrap_servers=["k"], payload_capture=True
        )
    except ValueError:
        pass
    else:
        raise AssertionError("payload configuration accepted")
