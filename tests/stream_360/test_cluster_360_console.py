from datetime import datetime, timezone

from services.product_query.stream_repository import BROKER_SAFE_SOURCE, StreamRepository


class FakeElasticsearch:
    def __init__(self, documents=None):
        self.documents = documents or {}
        self.requests = []

    def search(self, **request):
        self.requests.append(request)
        name = request["index"]
        hits = [
            {"_source": item, "sort": [item.get("name", item.get("partition_id", "")), str(index)]}
            for index, item in enumerate(self.documents.get(name, []))
        ]
        return {"hits": {"hits": hits[: request["size"]]}}


def test_cluster_related_query_is_isolated_bounded_and_safe():
    es = FakeElasticsearch()
    StreamRepository(es, timeout=2).related("brokers", "cluster-a", "tenant-a", "prod", size=51)
    request = es.requests[-1]
    assert request["index"] == "dataobs-kafka-brokers-v1-read"
    assert request["size"] == 51
    assert request["request_timeout"] == 2
    assert request["source"] is BROKER_SAFE_SOURCE
    assert "configuration" not in request["source"]
    assert "credentials" not in request["source"]
    assert "sasl" not in {field.lower() for field in request["source"]}
    filters = request["query"]["bool"]["filter"]
    assert {"term": {"tenant_id": "tenant-a"}} in filters
    assert {"term": {"environment": "prod"}} in filters
    assert {"term": {"cluster_id.keyword": "cluster-a"}} in filters
    assert request["sort"][-1] == {"_id": "asc"}


def test_related_search_after_and_topic_filters_are_forwarded():
    es = FakeElasticsearch()
    StreamRepository(es).related(
        "streams",
        "cluster-a",
        "tenant-a",
        "prod",
        size=20,
        search_after=["orders", "id"],
        search="orders*",
        health="degraded",
        retention_risk="at_risk",
        has_lag=True,
        sort="maximum_lag",
    )
    request = es.requests[-1]
    assert request["search_after"] == ["orders", "id"]
    assert "from" not in request and "from_" not in request
    assert request["query"]["bool"]["must"][0]["multi_match"]["query"] == "orders*"
    assert "wildcard" not in repr(request["query"])
    assert {"range": {"maximum_lag": {"gt": 0}}} in request["query"]["bool"]["filter"]


def test_cluster_health_uses_measured_failures_and_stale_evidence():
    old = "2020-01-01T00:00:00+00:00"
    docs = {
        "dataobs-kafka-brokers-v1-read": [{"name": "1", "health": "healthy", "controller": True, "observed_at": old}],
        "dataobs-kafka-topics-v1-read": [{"name": "orders", "health": "degraded", "observed_at": old}],
        "dataobs-kafka-consumer-groups-v1-read": [{"name": "billing", "observed_at": old}],
        "dataobs-kafka-connectors-v1-read": [
            {"name": "sink", "state": "failed", "failed_task_count": 1, "observed_at": old}
        ],
        "dataobs-kafka-partitions-v1-read": [
            {
                "partition_id": "0",
                "leader_available": False,
                "under_replicated": True,
                "offline_replicas": [2],
                "observed_at": old,
            }
        ],
    }
    result = StreamRepository(FakeElasticsearch(docs)).cluster_health(
        {"cluster_id": "cluster-a", "observed_at": datetime.now(timezone.utc).isoformat()}, "tenant-a", "prod"
    )
    assert result["health"] == "critical"
    assert result["leaderless_partition_count"] == 1
    assert result["under_replicated_partition_count"] == 1
    assert result["offline_replica_count"] == 1
    assert result["failed_connector_count"] == 1
    assert result["stale_resource_count"] == 5
    assert result["data_status"] == "stale"


def test_missing_partition_evidence_is_unknown_not_zero():
    docs = {
        "dataobs-kafka-brokers-v1-read": [{"name": "1", "health": "healthy", "controller": True}],
        "dataobs-kafka-topics-v1-read": [{"name": "orders", "health": "healthy"}],
    }
    result = StreamRepository(FakeElasticsearch(docs)).cluster_health({"cluster_id": "cluster-a"}, "tenant-a", "prod")
    assert result["health"] == "unknown"
    assert result["partition_count"] is None
    assert result["under_replicated_partition_count"] is None
    assert result["leaderless_partition_count"] is None
    assert "partitions_projection" in result["missing_inputs"]


def test_measured_zero_is_distinct_from_unknown():
    docs = {
        "dataobs-kafka-brokers-v1-read": [{"name": "1", "health": "healthy", "controller": True}],
        "dataobs-kafka-topics-v1-read": [{"name": "orders", "health": "healthy"}],
        "dataobs-kafka-consumer-groups-v1-read": [{"name": "billing"}],
        "dataobs-kafka-connectors-v1-read": [{"name": "sink", "state": "running", "failed_task_count": 0}],
        "dataobs-kafka-partitions-v1-read": [
            {"partition_id": "0", "leader_available": True, "under_replicated": False, "offline_replicas": []}
        ],
    }
    result = StreamRepository(FakeElasticsearch(docs)).cluster_health({"cluster_id": "cluster-a"}, "tenant-a", "prod")
    assert result["health"] == "healthy"
    assert result["leaderless_partition_count"] == 0
    assert result["failed_connector_count"] == 0
    assert result["reason_codes"] == ["measured_failures_zero"]
