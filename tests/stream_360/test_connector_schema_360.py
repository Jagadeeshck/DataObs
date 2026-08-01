from services.kafka_observer.repository import ElasticsearchObserverRepository, MemoryObserverRepository
from services.kafka_observer.service import KafkaObserverService


class ES:
    def __init__(self):
        self.writes = []

    def index(self, **kwargs):
        self.writes.append(kwargs)
        return {"result": "created"}


class Checkpoints:
    def __init__(self):
        self.values = {}

    def load(self, key):
        return self.values.get(key)

    def save(self, key, value):
        self.values[key] = value


class Admin:
    def inventory(self):
        return {"cluster_id": "cluster-a", "topics": [], "consumer_groups": []}

    def offsets(self, maximum):
        return {"offsets": []}


class Collector:
    def __init__(self, payload):
        self.payload = payload

    def collect(self):
        return self.payload


def repository():
    return ElasticsearchObserverRepository(ES(), "tenant-a", "test", "integration-a")


def test_connector_projection_is_scoped_bounded_and_safe():
    repo = repository()
    repo.save_connector_projection(
        {
            "cluster_id": "cluster-a",
            "data_status": "complete",
            "connectors": [
                {
                    "connector_id": "orders",
                    "name": "orders",
                    "state": "RUNNING",
                    "task_count": 1,
                    "failed_task_count": 0,
                    "task_states": [{"id": 0, "state": "RUNNING"}],
                    "config": {"unsafe": "value"},
                    "config_fingerprint": "sha256",
                }
            ],
        }
    )
    write = repo.es.writes[0]
    assert write["id"] == "tenant-a:test:cluster-a:orders"
    assert write["document"]["health"] == "healthy"
    assert "config" not in write["document"]


def test_schema_projection_excludes_body_and_orders_versions():
    repo = repository()
    repo.save_schema_projection(
        {
            "cluster_id": "cluster-a",
            "data_status": "complete",
            "schemas": [
                {
                    "subject_id": "orders",
                    "version": 1,
                    "schema_id": 1,
                    "schema": "unsafe body",
                    "fingerprint": "a",
                    "references": [],
                },
                {"subject_id": "orders", "version": 2, "schema_id": 2, "fingerprint": "b", "references": []},
            ],
        }
    )
    document = repo.es.writes[0]["document"]
    assert [row["version"] for row in document["versions"]] == [2, 1]
    assert "schema" not in document
    assert all("schema" not in version for version in document["versions"])


def test_checkpoint_advances_only_after_projection_persistence():
    checkpoints, repo = Checkpoints(), MemoryObserverRepository()
    service = KafkaObserverService(
        Admin(),
        checkpoints,
        [],
        repository=repo,
        connect_collector=Collector({"connectors": [], "data_status": "complete"}),
    )
    service.collect_capability("connectors")
    assert checkpoints.values["connectors"]["last_successful_collection"]

    class Broken(MemoryObserverRepository):
        def save_schema_projection(self, payload):
            raise RuntimeError("write failed")

    checkpoints.values["schemas"] = {"last_successful_collection": "previous"}
    failing = KafkaObserverService(
        Admin(),
        checkpoints,
        [],
        repository=Broken(),
        schema_collector=Collector({"schemas": [], "data_status": "complete"}),
    )
    try:
        failing.collect_capability("schemas")
    except RuntimeError:
        pass
    assert checkpoints.values["schemas"]["last_successful_collection"] == "previous"
    assert checkpoints.values["schemas"]["consecutive_failure_count"] == 1
