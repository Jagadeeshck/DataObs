"""Release regressions for observed offsets, bounded collection and truthful lag."""

from concurrent.futures import Future
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from confluent_kafka import TopicPartition

from integrations.kafka.admin_client import ConfluentReadOnlyAdmin
from packages.pathways.lag import estimate_lag
from services.kafka_observer.offsets import OffsetSample, calculate_lag, lag_summary, lag_velocity

NOW = datetime.now(timezone.utc)


@pytest.mark.parametrize(
    ("high", "committed", "expected", "status"),
    [
        (100, 100, 0, "complete"),
        (100, 0, 100, "complete"),
        (100, None, None, "partial"),
        (None, 20, None, "partial"),
        (100, -1, None, "unknown"),
        (100, 101, None, "unknown"),
        (-1, 0, None, "unknown"),
    ],
)
def test_lag_truth_table(high, committed, expected, status):
    result = calculate_lag(OffsetSample(0, high, committed, NOW))
    assert result["lag_messages"] == expected
    assert result["data_status"] == status
    assert estimate_lag(high, committed)["lag_messages"] == expected
    if high == 100 and committed == 101:
        assert result["reason_code"] == "inconsistent_offset_window"


def row(partition, high, committed, **extra):
    return dict(
        group_id="billing",
        topic="orders",
        partition=partition,
        high_watermark=high,
        committed_offset=committed,
        **extra,
    )


def test_rollups_require_all_partitions_and_preserve_zero_and_skew():
    rows = [row(0, 10, 0), row(1, 20, 5), row(2, 30, 30)]
    assert lag_summary(rows)["total_lag"] == 25
    assert lag_summary(rows)["maximum_lag"] == 15
    caught_up = [dict(item, committed_offset=item["high_watermark"]) for item in rows]
    assert lag_summary(caught_up)["total_lag"] == lag_summary(caught_up)["maximum_lag"] == 0
    for unavailable in ([], rows + [row(3, None, 1)], rows + [row(3, 10, None)], rows + [row(3, 10, 11)]):
        assert lag_summary(unavailable)["total_lag"] is None
        assert lag_summary(unavailable)["maximum_lag"] is None
    assert lag_summary(rows, partial=True)["total_lag"] is None
    assert lag_summary([row(0, 10, 10, data_status="stale")])["data_status"] == "stale"
    assert lag_velocity([(NOW, 0), (NOW + timedelta(seconds=10), 0)])["messages_per_second"] == 0
    assert lag_velocity([(NOW, 0)])["messages_per_second"] is None


class Admin:
    def __init__(self, *, failed=False):
        self.groups = []
        self.failed = failed

    def list_consumer_group_offsets(self, requests, **kwargs):
        group = requests[0].group_id
        self.groups.append(group)
        future = Future()
        if self.failed:
            future.set_exception(RuntimeError("unavailable"))
        else:
            future.set_result(
                SimpleNamespace(
                    topic_partitions=[
                        TopicPartition("orders", 0, 0),
                        TopicPartition("orders", 1, 5),
                        TopicPartition("orders", 2, 30),
                    ]
                )
            )
        return {group: future}


class Watermarks:
    def committed(self, *args, **kwargs):
        raise AssertionError("must not read the observer's own consumer group")

    def get_watermark_offsets(self, partition, **kwargs):
        return 0, [10, 20, 30][partition.partition]


def probe(*, failed=False):
    instance = ConfluentReadOnlyAdmin.__new__(ConfluentReadOnlyAdmin)
    instance._client, instance._consumer, instance.timeout = Admin(failed=failed), Watermarks(), 1
    return instance


def test_observed_group_is_selected_and_inactive_commits_are_observed():
    instance = probe()
    result = instance.offsets({"cluster_id": "c", "consumer_groups": [{"group_id": "billing", "members": []}]})
    assert instance._client.groups == ["billing"]
    assert [item["committed_offset"] for item in result["offsets"]] == [0, 5, 30]
    assert result["consumer_groups"][0]["total_lag"] == 25
    assert result["consumer_groups"][0]["maximum_lag"] == 15
    assert not result["continuation"]


def test_uncommitted_assignment_and_failed_commit_read_are_not_zero():
    result = probe(failed=True).offsets(
        {
            "consumer_groups": [
                {
                    "group_id": "new",
                    "members": [{"member_id": "m", "assignments": [{"topic": "orders", "partition": 0}]}],
                }
            ]
        }
    )
    assert result["offsets"][0]["committed_offset"] is None
    assert "committed_offset" in result["offsets"][0]["missing_inputs"]
    assert result["consumer_groups"][0]["total_lag"] is None
    assert result["data_status"] == "partial"


def test_collection_limit_truncates_rollup_and_rejects_unbounded_requests():
    instance = probe()
    result = instance.offsets({"consumer_groups": [{"group_id": "billing", "members": []}]}, maximum=2)
    assert result["count"] == 2 and result["continuation"]
    assert result["consumer_groups"][0]["total_lag"] is None
    for maximum in (0, -1, 100_001):
        with pytest.raises(ValueError):
            instance.offsets({}, maximum=maximum)


def test_group_and_topic_projections_are_scoped_and_missing_rollups_are_not_zero():
    from services.kafka_observer.repository import ElasticsearchObserverRepository

    class ES:
        def __init__(self):
            self.writes = []

        def update(self, **kwargs):
            self.writes.append(kwargs)

    es = ES()
    repo = ElasticsearchObserverRepository(es, "tenant-a", "prod", "kafka-a")
    rows = [row(0, 10, 0), row(1, 20, 5), row(2, 30, 30)]
    payload = {"cluster_id": "c", "offsets": rows, "data_status": "complete"}
    repo.save_offset_projection(payload)
    assert len(es.writes) == 2
    for write in es.writes:
        assert write["id"].startswith("tenant-a:prod:c:")
        assert write["doc"]["tenant_id"] == "tenant-a"
        assert write["doc"]["environment"] == "prod"
        assert write["doc"]["total_lag"] == 25 and write["doc"]["maximum_lag"] == 15
    repo.save_offset_projection(payload | {"offsets": rows + [row(3, None, 0)]})
    assert all(write["doc"]["total_lag"] is None for write in es.writes[-2:])
    repo.save_offset_projection(payload | {"offsets": [], "consumer_groups": [{"group_id": "new"}]})
    assert es.writes[-1]["doc"]["total_lag"] is None


def test_offset_checkpoint_stays_put_when_projection_fails():
    from services.kafka_observer.checkpoint_store import MemoryCheckpointStore
    from services.kafka_observer.repository import MemoryObserverRepository
    from services.kafka_observer.service import KafkaObserverService

    class Source:
        def offsets(self, maximum):
            return {"cluster_id": "c", "offsets": [row(0, 10, 0)]}

    class Broken(MemoryObserverRepository):
        def save_offset_projection(self, payload):
            raise RuntimeError("Elasticsearch rejected projection")

    cp = MemoryCheckpointStore()
    cp.save("offsets", {"last_successful_collection": "previous"})
    service = KafkaObserverService(Source(), cp, [], repository=Broken())
    with pytest.raises(RuntimeError):
        service.collect_capability("offsets")
    assert cp.load("offsets")["last_successful_collection"] == "previous"


def test_missing_group_inventory_is_not_a_measured_empty_group_set():
    from services.kafka_observer.groups import group_projection

    assert group_projection({"consumer_groups": []})["count"] == 0
    missing = {"consumer_groups": [], "warnings": ["consumer group inventory unavailable: TimeoutError"]}
    assert group_projection(missing)["count"] is None
    assert group_projection(missing)["data_status"] == "source_unavailable"
    result = probe().offsets(missing)
    assert result["data_status"] == "partial"


def test_inventory_processing_has_explicit_topic_and_partition_bounds():
    from types import SimpleNamespace

    instance = probe()
    instance.MAX_TOPICS, instance.MAX_PARTITIONS = 1, 1

    def partition(n):
        return SimpleNamespace(id=n, leader=1, replicas=[1], isrs=[1])

    topic = SimpleNamespace(partitions={i: partition(i) for i in range(3)})
    metadata = SimpleNamespace(cluster_id="c", controller_id=1, brokers={}, topics={"z": topic, "a": topic})
    instance._client = SimpleNamespace(list_topics=lambda **kwargs: metadata)
    instance._topic_configs = lambda *_: {}
    instance._consumer_groups = lambda: ([], [])
    result = instance.inventory()
    assert [item["name"] for item in result["topics"]] == ["a"]
    assert len(result["topics"][0]["partitions"]) == 1
    assert set(result["warnings"]) == {"topic_inventory_truncated", "partition_inventory_truncated"}
