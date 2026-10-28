"""Single-broker release evidence; does not claim multi-broker certification."""

import json
import os
import time
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("KAFKA_BOOTSTRAP_SERVERS"), reason="requires disposable Kafka fixture")


def test_real_partition_skew_catchup_and_observer_restart(tmp_path):
    from confluent_kafka import Consumer, Producer, TopicPartition
    from confluent_kafka.admin import AdminClient, NewTopic

    from integrations.kafka.admin_client import ConfluentReadOnlyAdmin

    config = {"bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"], "broker.address.family": "v4"}
    identifier = uuid.uuid4().hex[:12]
    topic, group = f"team1-lag-{identifier}", f"team1-consumer-{identifier}"
    admin = AdminClient(config)
    for future in admin.create_topics([NewTopic(topic, 3, 1)]).values():
        future.result(timeout=20)
    producer = Producer(config)
    for partition, count in enumerate((10, 20, 30)):
        for number in range(count):
            producer.produce(topic, str(number).encode(), partition=partition)
    assert producer.flush(20) == 0
    consumer = Consumer(config | {"group.id": group, "enable.auto.commit": False})

    def consume(partition, start, count):
        consumer.assign([TopicPartition(topic, partition, start)])
        deadline = time.monotonic() + 20
        received = 0
        while received < count and time.monotonic() < deadline:
            message = consumer.poll(0.25)
            if message is not None:
                assert not message.error(), message.error()
                received += 1
        assert received == count
        consumer.commit(offsets=[TopicPartition(topic, partition, start + count)], asynchronous=False)

    def observe():
        observer = ConfluentReadOnlyAdmin(config | {"client.id": "team1-audit"}, timeout=10)
        try:
            inventory = observer.inventory()
            assert next(item for item in inventory["topics"] if item["name"] == topic)["partition_count"] == 3
            target = next(item for item in inventory["consumer_groups"] if item["group_id"] == group)
            result = observer.offsets(inventory | {"consumer_groups": [target]})
            assert [item["high_watermark"] for item in result["offsets"]] == [10, 20, 30]
            return result
        finally:
            observer.close()

    try:
        for partition, count in enumerate((0, 5, 30)):
            consume(partition, 0, count)
        partial = observe()
        assert [row["committed_offset"] for row in partial["offsets"]] == [0, 5, 30]
        assert partial["consumer_groups"][0]["total_lag"] == 25
        assert partial["consumer_groups"][0]["maximum_lag"] == 15
        # Reopening the observer must read the target's same committed offsets.
        assert observe() == partial
        for partition, start, count in ((0, 0, 10), (1, 5, 15)):
            consume(partition, start, count)
        caught_up = observe()
        assert caught_up["consumer_groups"][0]["total_lag"] == 0
        assert caught_up["consumer_groups"][0]["maximum_lag"] == 0
        assert observe() == caught_up
        evidence = {
            "broker_count": 1,
            "partitions": 3,
            "produced": 60,
            "partial": partial,
            "caught_up": caught_up,
            "observer_restart_replay": "PASS",
        }
        (tmp_path / "real-kafka-lag.json").write_text(json.dumps(evidence, sort_keys=True, indent=2))
        output = os.getenv("TEAM1_KAFKA_EVIDENCE_PATH")
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(json.dumps(evidence, sort_keys=True, indent=2))
        print(json.dumps(evidence, sort_keys=True))
    finally:
        consumer.close()
