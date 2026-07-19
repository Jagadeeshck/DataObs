from datetime import datetime, timedelta, timezone

from integrations.kafka.config import KafkaObserverConfig
from integrations.kafka_connect.actions import ApprovedRestartService, RestartRequest
from integrations.kafka_connect.collector import KafkaConnectCollector
from integrations.schema_registry.collector import SchemaRegistryCollector
from services.kafka_observer.broker_metrics import broker_metric_status
from services.kafka_observer.errors import CollectionError
from services.kafka_observer.leases import DurableLeases, MemoryLeaseRepository
from services.kafka_observer.offsets import lag_velocity


def test_lease_excludes_another_owner_and_can_be_released():
    leases = DurableLeases(MemoryLeaseRepository())
    assert leases.acquire("inventory", "one", 30)
    assert not leases.acquire("inventory", "two", 30)
    leases.release("inventory", "one")
    assert leases.acquire("inventory", "two", 30)


def test_lag_velocity_uses_robust_median_slope():
    now = datetime.now(timezone.utc)
    samples = [
        (now, 0),
        (now + timedelta(seconds=10), 10),
        (now + timedelta(seconds=20), 1_000),  # isolated spike
        (now + timedelta(seconds=30), 30),
    ]
    result = lag_velocity(samples)
    assert result["method"] == "median_pairwise_slope"
    assert result["messages_per_second"] == 1.0


def test_runtime_config_rejects_unallowlisted_bootstrap_and_literal_secret():
    base = {"tenant_id": "t", "environment": "production", "integration_id": "i", "bootstrap_servers": ["k:9092"]}
    try:
        KafkaObserverConfig.model_validate(base | {"bootstrap_server_allowlist": ["other:9092"]})
        assert False
    except ValueError:
        pass
    try:
        KafkaObserverConfig.model_validate(
            base
            | {
                "security": {
                    "protocol": "SASL_SSL",
                    "sasl_mechanism": "PLAIN",
                    "username_ref": "user",
                    "password_ref": "password",
                }
            }
        )
        assert False
    except ValueError:
        pass


def test_collection_error_never_persists_exception_message():
    error = CollectionError.from_exception("offsets", "kafka", RuntimeError("password=hunter2"), 2)
    assert "hunter2" not in str(error.document())
    assert error.retry_count == 2


class _Connect:
    def connectors(self):
        return ["sink"]

    def connector_config(self, name):
        return {"connector.class": "JdbcSink", "password": "do-not-store"}

    def status(self, name):
        return {"connector": {"state": "RUNNING"}, "tasks": [{"id": 0, "state": "FAILED"}]}

    def restart_failed_task(self, name, task_id, *, approved):
        self.restarted = approved


def test_connect_collector_drops_config_and_restart_is_approved_idempotent():
    client = _Connect()
    result = KafkaConnectCollector(client).collect()
    assert "config" not in result["connectors"][0]
    action = ApprovedRestartService(client, {"sink"})
    request = RestartRequest("sink", 0, "operator", "recover", "once", "approval-1")
    first = action.restart(request, approved=True)
    assert action.restart(request, approved=True) == first


class _Registry:
    def subjects(self):
        return ["orders-value"]

    def versions(self, subject):
        return [1]

    def compatibility(self, subject):
        return {"compatibilityLevel": "BACKWARD"}

    def schema(self, subject, version):
        return {"id": 7, "schemaType": "AVRO", "schema": '{"name":"Order","fields":[]}'}


def test_schema_collector_persists_fingerprint_not_body():
    result = SchemaRegistryCollector(_Registry()).collect()["schemas"][0]
    assert "schema" not in result
    assert len(result["fingerprint"]) == 64
    assert broker_metric_status()["data_status"] == "not_configured"
