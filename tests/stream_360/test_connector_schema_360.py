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


def test_nested_connector_and_schema_metadata_do_not_leak_raw_inputs():
    repo = repository()
    repo.save_connector_projection(
        {
            "connectors": [
                {
                    "connector_id": "orders",
                    "task_states": [
                        {"id": 1, "state": "RUNNING", "password": "sentinel", "config": {"sasl": "sentinel"}}
                    ],
                }
            ]
        }
    )
    repo.save_schema_projection(
        {
            "schemas": [
                {
                    "subject_id": "orders",
                    "version": 1,
                    "compatibility_mode": "BACKWARD",
                    "semantic_summary": {"field_count": 2, "raw_schema": "sentinel"},
                    "references": [{"name": "ref", "subject": "shared", "version": 1, "token": "sentinel"}],
                }
            ]
        }
    )
    assert "sentinel" not in repr(repo.es.writes)
    schema = repo.es.writes[-1]["document"]
    assert schema["health"] == "unknown"
    assert schema["reason_codes"] == ["compatibility_not_evaluated"]


def test_schema_runtime_rejects_nested_payload_and_credentials():
    import pytest

    from services.kafka_observer.schema_intelligence_repository import ElasticsearchSchemaIntelligenceRepository

    for field in ("raw_schema", "schema", "payload", "password", "token", "credentials", "sample"):
        with pytest.raises(ValueError, match="forbidden"):
            ElasticsearchSchemaIntelligenceRepository._safe({"evidence": [{field: "sentinel"}]})


def test_schema_reads_are_fixed_scoped_bounded_and_source_allowlisted():
    import pytest

    from services.kafka_observer.schema_intelligence_repository import (
        SAFE_SOURCE,
        SUBJECTS,
        ElasticsearchSchemaIntelligenceRepository,
    )

    class Search:
        def __init__(self):
            self.requests = []

        def search(self, **kwargs):
            self.requests.append(kwargs)
            return {"hits": {"hits": []}}

    es = Search()
    repo = ElasticsearchSchemaIntelligenceRepository(es)
    with pytest.raises(ValueError):
        repo.search("*", "tenant-a", "prod")
    repo.search(SUBJECTS, "tenant-a", "prod", subject_id="subject", size=100_000)
    request = es.requests[-1]
    assert request["size"] == 200 and request["source"] is SAFE_SOURCE
    assert request["sort"][-1] == {"_id": "asc"}
    assert request["query"]["bool"]["filter"][:2] == [
        {"term": {"tenant_id": "tenant-a"}},
        {"term": {"environment": "prod"}},
    ]
    assert not {"schema", "raw_schema", "payload", "credentials", "token"}.intersection(request["source"])


def test_same_schema_subject_is_isolated_across_tenants_and_environments():
    from packages.streaming.schema_intelligence import SchemaIdentity

    a = SchemaIdentity("tenant-a", "prod", "registry", "orders")
    b = SchemaIdentity("tenant-b", "prod", "registry", "orders")
    c = SchemaIdentity("tenant-a", "stage", "registry", "orders")
    assert len({item.subject_id for item in (a, b, c)}) == 3
    assert len({item.version_id(1, "same-fingerprint") for item in (a, b, c)}) == 3
