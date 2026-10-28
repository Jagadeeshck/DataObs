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

    MAX_TOPICS = 1000
    MAX_GROUPS = 1000
    MAX_PARTITIONS = 10000

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
        names = sorted(metadata.topics)[: self.MAX_TOPICS]
        if len(metadata.topics) > len(names):
            warnings.append("topic_inventory_truncated")
        remaining = self.MAX_PARTITIONS
        topics = []
        for name in names:
            topic = metadata.topics[name]
            partitions = sorted(topic.partitions.values(), key=lambda item: item.id)[:remaining]
            remaining -= len(partitions)
            if len(partitions) < len(topic.partitions):
                warnings.append("partition_inventory_truncated")
            topics.append(
                {
                    "name": name,
                    "id": str(getattr(topic, "topic_id", name)),
                    "internal": name.startswith("__"),
                    "partition_count": len(topic.partitions),
                    "replication_factor": max((len(p.replicas) for p in partitions), default=0) if partitions else None,
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
                        for p in partitions
                    ],
                }
            )
        return {
            "cluster_id": metadata.cluster_id,
            "controller_id": metadata.controller_id,
            "brokers": [
                {"id": b.id, "host": b.host, "port": b.port, "rack": getattr(b, "rack", None)}
                for b in metadata.brokers.values()
            ],
            "topics": topics,
            "consumer_groups": groups,
            "warnings": sorted(set(warnings)),
        }

    def offsets(self, inventory: dict[str, Any] | None = None, *, maximum: int = 100_000) -> dict[str, Any]:
        """Read commits for the observed group, including inactive committed partitions."""
        from confluent_kafka import ConsumerGroupTopicPartitions, TopicPartition

        from services.kafka_observer.offsets import lag_summary

        if not 1 <= maximum <= 100_000:
            raise ValueError("offset collection limit must be between 1 and 100000")
        inventory = self.inventory() if inventory is None else inventory
        rows: list[dict[str, Any]] = []
        truncated = False
        groups_truncated = len(inventory.get("consumer_groups", [])) > maximum
        group_results = []
        for group in inventory.get("consumer_groups", [])[:maximum]:
            assignments = {
                (assignment["topic"], assignment["partition"]): member
                for member in group.get("members", [])
                for assignment in member.get("assignments", [])
            }
            try:
                # Consumer.committed() reads that Consumer's own group. The Admin
                # API explicitly selects the group being observed instead.
                futures = self._client.list_consumer_group_offsets(
                    [ConsumerGroupTopicPartitions(group["group_id"])], request_timeout=self.timeout
                )
                result = futures[group["group_id"]].result(timeout=self.timeout)
                commits = {(item.topic, item.partition): item for item in result.topic_partitions}
                commit_status = "complete"
            except Exception:
                commits, commit_status = {}, "source_unavailable"
            keys = sorted(set(assignments) | set(commits))
            first_row = len(rows)
            for topic, partition_id in keys:
                if len(rows) >= maximum:
                    truncated = True
                    break
                member = assignments.get((topic, partition_id))
                commit = commits.get((topic, partition_id))
                offset = (
                    commit.offset
                    if commit is not None and not getattr(commit, "error", None) and commit.offset >= 0
                    else None
                )
                try:
                    low, high = self._consumer.get_watermark_offsets(
                        TopicPartition(topic, partition_id), timeout=self.timeout, cached=False
                    )
                    low = low if low >= 0 else None
                    high = high if high >= 0 else None
                except Exception:
                    low, high = None, None
                missing = ["last_stable_offset"]
                if offset is None:
                    missing.append("committed_offset")
                if high is None:
                    missing.append("high_watermark")
                rows.append(
                    {
                        "group_id": group["group_id"],
                        "topic": topic,
                        "partition": partition_id,
                        "log_start_offset": low,
                        "high_watermark": high,
                        "last_stable_offset": None,
                        "committed_offset": offset,
                        "commit_metadata": None,
                        "member_id": member.get("member_id") if member else None,
                        "data_status": "partial" if commit_status == "complete" else commit_status,
                        "missing_inputs": missing,
                    }
                )
            group_rows = rows[first_row:]
            group_results.append(
                {
                    "group_id": group["group_id"],
                    **lag_summary(group_rows, partial=truncated or bool(inventory.get("warnings"))),
                }
            )
            if truncated:
                break
        return {
            "cluster_id": inventory.get("cluster_id"),
            "offsets": rows,
            "consumer_groups": group_results,
            "topic_ids": {topic["name"]: topic.get("id") or topic["name"] for topic in inventory.get("topics", [])},
            "count": len(rows),
            "continuation": truncated or groups_truncated,
            "data_status": (
                "partial"
                if truncated
                or groups_truncated
                or bool(inventory.get("warnings"))
                or any(group["data_status"] != "complete" for group in group_results)
                else "complete"
            ),
        }

    def _topic_configs(self, metadata: Any) -> dict[str, dict[str, Any]]:
        from confluent_kafka.admin import ConfigResource

        resources = [
            ConfigResource(ConfigResource.Type.TOPIC, name) for name in sorted(metadata.topics)[: self.MAX_TOPICS]
        ]
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
            if getattr(listing, "errors", None):
                warnings.append("consumer group inventory unavailable: partial listing")
            valid = sorted(getattr(listing, "valid", listing), key=lambda item: item.group_id)
            if len(valid) > self.MAX_GROUPS:
                warnings.append("consumer_group_inventory_truncated")
            valid = valid[: self.MAX_GROUPS]
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
                if len(group.members) > 1000:
                    warnings.append("consumer_group_members_truncated")
                for member in group.members[:1000]:
                    assignments = [
                        {"topic": tp.topic, "partition": tp.partition}
                        for tp in member.assignment.topic_partitions[: self.MAX_PARTITIONS]
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
