from datetime import datetime, timedelta, timezone

from services.kafka_observer.leases import MemoryLeaseRepository
from services.kafka_observer.repository import ElasticsearchObserverRepository


class RecordingElasticsearch:
    def __init__(self):
        self.writes = []

    def index(self, **kwargs):
        self.writes.append(kwargs)
        return {"result": "created"}


def test_inventory_projection_writes_canonical_top_level_fields():
    es = RecordingElasticsearch()
    repository = ElasticsearchObserverRepository(es, "tenant-a", "prod", "kafka-a")
    repository.save_collection(
        "inventory",
        {
            "cluster_id": "cluster-a",
            "controller_id": 1,
            "brokers": [{"id": 1, "host": "broker", "port": 9092, "rack": "a"}],
            "topics": [
                {
                    "id": "topic-id",
                    "name": "orders",
                    "partition_count": 1,
                    "replication_factor": 2,
                    "config": {"cleanup.policy": "delete", "retention.ms": "60000"},
                    "partitions": [
                        {"partition": 0, "leader": 1, "replicas": [1, 2], "isr": [1], "leader_available": True}
                    ],
                }
            ],
            "consumer_groups": [{"group_id": "billing", "state": "STABLE", "members": []}],
        },
        {"last_successful_collection": "now"},
    )
    topic = next(write["document"] for write in es.writes if write["index"] == "dataobs-kafka-topics-v1-write")
    assert topic["topic"] == "orders"
    assert topic["retention_ms"] == 60000
    assert topic["health"] == "degraded"
    assert "document" not in topic
    assert {"tenant_id", "environment", "integration_id", "schema_version", "observed_at"} <= topic.keys()


def test_expired_lease_changes_owner_and_increments_fencing_token():
    leases = MemoryLeaseRepository()
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
    assert leases.acquire_lease("offsets", "old", expired)
    old_token = leases.values["offsets"]["fencing_token"]
    assert leases.acquire_lease("offsets", "new", future)
    assert leases.values["offsets"]["fencing_token"] == old_token + 1
    leases.release_lease("offsets", "old")
    assert leases.values["offsets"]["owner"] == "new"


def test_live_lease_contention_fails_closed():
    leases = MemoryLeaseRepository()
    future = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
    assert leases.acquire_lease("inventory", "one", future)
    assert not leases.acquire_lease("inventory", "two", future)
