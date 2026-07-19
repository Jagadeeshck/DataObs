from __future__ import annotations

from typing import Any, Protocol

from .security import redact

APPROVED_TOPIC_CONFIGS = {
    "retention.ms",
    "retention.bytes",
    "cleanup.policy",
    "min.insync.replicas",
    "max.message.bytes",
    "compression.type",
    "segment.ms",
    "segment.bytes",
    "unclean.leader.election.enable",
}


class ReadOnlyAdmin(Protocol):
    def inventory(self) -> dict[str, Any]: ...
    def offsets(self, inventory: dict[str, Any] | None = None, *, maximum: int = 100_000) -> dict[str, Any]: ...


class ConfluentReadOnlyAdmin:
    """Thin adapter; imports confluent-kafka only when instantiated."""

    def __init__(self, config: dict[str, Any], *, timeout: float = 10):
        from confluent_kafka import Consumer
        from confluent_kafka.admin import AdminClient

        self._client = AdminClient(config)
        self._consumer = Consumer(
            config | {"group.id": f"{config.get('client.id', 'dataobs')}-offset-reader", "enable.auto.commit": False}
        )
        self.timeout = timeout

    def test_connection(self) -> dict[str, Any]:
        metadata = self._client.list_topics(timeout=self.timeout)
        return {"ok": True, "cluster_id": metadata.cluster_id, "broker_count": len(metadata.brokers)}

    def inventory(self) -> dict[str, Any]:
        metadata = self._client.list_topics(timeout=self.timeout)
        topic_configs = self._topic_configs(metadata)
        groups, warnings = self._consumer_groups()
        return {
            "cluster_id": metadata.cluster_id,
            "controller_id": metadata.controller_id,
            "brokers": [
                {"id": b.id, "host": b.host, "port": b.port, "rack": getattr(b, "rack", None)}
                for b in metadata.brokers.values()
            ],
            "topics": [
                {
                    "name": name,
                    "id": str(getattr(topic, "topic_id", name)),
                    "internal": name.startswith("__"),
                    "partition_count": len(topic.partitions),
                    "replication_factor": max((len(p.replicas) for p in topic.partitions.values()), default=0),
                    "config": topic_configs.get(name, {}),
                    "partitions": [
                        {
                            "partition": p.id,
                            "leader": p.leader,
                            "replicas": p.replicas,
                            "isr": p.isrs,
                            "offline_replicas": sorted(set(p.replicas) - set(p.isrs)),
                            "leader_available": p.leader >= 0,
                        }
                        for p in topic.partitions.values()
                    ],
                }
                for name, topic in metadata.topics.items()
            ],
            "consumer_groups": groups,
            "warnings": warnings,
        }

    def offsets(self, inventory: dict[str, Any] | None = None, *, maximum: int = 100_000) -> dict[str, Any]:
        """Collect assigned group offsets without constructing a topic/group Cartesian product."""
        from confluent_kafka import TopicPartition

        inventory = inventory or self.inventory()
        combinations: list[tuple[str, TopicPartition, dict[str, Any] | None]] = []
        for group in inventory.get("consumer_groups", []):
            assignments: dict[tuple[str, int], dict[str, Any]] = {}
            for member in group.get("members", []):
                for assignment in member.get("assignments", []):
                    assignments[(assignment["topic"], assignment["partition"])] = member
            for (topic, partition), member in assignments.items():
                if len(combinations) >= maximum:
                    break
                combinations.append((group["group_id"], TopicPartition(topic, partition), member))
            if len(combinations) >= maximum:
                break
        rows: list[dict[str, Any]] = []
        by_group: dict[str, list[tuple[TopicPartition, dict[str, Any] | None]]] = {}
        for group_id, partition, member in combinations:
            by_group.setdefault(group_id, []).append((partition, member))
        for group_id, values in by_group.items():
            requested = [partition for partition, _ in values]
            try:
                committed = self._consumer.committed(requested, timeout=self.timeout)
            except Exception:
                committed = [TopicPartition(item.topic, item.partition, -1) for item in requested]
            commits = {(item.topic, item.partition): item for item in committed}
            for partition, member in values:
                status = "complete"
                try:
                    low, high = self._consumer.get_watermark_offsets(partition, timeout=self.timeout, cached=False)
                except Exception:
                    low, high, status = None, None, "source_unavailable"
                commit = commits[(partition.topic, partition.partition)]
                rows.append(
                    {
                        "group_id": group_id,
                        "topic": partition.topic,
                        "partition": partition.partition,
                        "log_start_offset": low,
                        "high_watermark": high,
                        # librdkafka does not expose LSO separately through this API.
                        "last_stable_offset": None,
                        "committed_offset": commit.offset if commit.offset >= 0 else None,
                        "commit_metadata": None,
                        "member_id": member.get("member_id") if member else None,
                        "data_status": "partial" if status == "complete" else status,
                        "missing_inputs": ["last_stable_offset"],
                    }
                )
        return {
            "cluster_id": inventory.get("cluster_id"),
            "offsets": rows,
            "count": len(rows),
            "continuation": len(combinations) >= maximum,
            "data_status": "partial" if len(combinations) >= maximum else "complete",
        }

    def _topic_configs(self, metadata: Any) -> dict[str, dict[str, Any]]:
        from confluent_kafka.admin import ConfigResource

        resources = [ConfigResource(ConfigResource.Type.TOPIC, name) for name in metadata.topics]
        futures = self._client.describe_configs(resources, request_timeout=self.timeout)
        result: dict[str, dict[str, Any]] = {}
        for resource, future in futures.items():
            try:
                values = future.result(timeout=self.timeout)
                result[resource.name] = redact(
                    {name: entry.value for name, entry in values.items() if name in APPROVED_TOPIC_CONFIGS}
                )
            except Exception:
                result[resource.name] = {}
        return result

    def _consumer_groups(self) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        try:
            listing = self._client.list_consumer_groups(request_timeout=self.timeout).result(timeout=self.timeout)
            valid = getattr(listing, "valid", listing)
            descriptions = self._client.describe_consumer_groups(
                [g.group_id for g in valid], request_timeout=self.timeout
            )
        except Exception as error:
            return [], [f"consumer group inventory unavailable: {type(error).__name__}"]
        groups: list[dict[str, Any]] = []
        for group_id, future in descriptions.items():
            try:
                group = future.result(timeout=self.timeout)
                members = []
                for member in group.members:
                    assignments = [
                        {"topic": tp.topic, "partition": tp.partition} for tp in member.assignment.topic_partitions
                    ]
                    members.append(
                        {
                            "member_id": member.member_id,
                            "client_id": member.client_id,
                            "host": member.host,
                            "assignments": assignments,
                        }
                    )
                groups.append(
                    {
                        "group_id": group_id,
                        "state": str(group.state),
                        "protocol": getattr(group, "partition_assignor", None),
                        "coordinator": getattr(getattr(group, "coordinator", None), "id", None),
                        "member_count": len(members),
                        "members": members,
                    }
                )
            except Exception as error:
                warnings.append(f"group {group_id} unavailable: {type(error).__name__}")
        return groups, warnings

    def close(self) -> None:
        self._consumer.close()
