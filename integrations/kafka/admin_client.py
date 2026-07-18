from __future__ import annotations

from typing import Any, Protocol


class ReadOnlyAdmin(Protocol):
    def inventory(self) -> dict[str, Any]: ...


class ConfluentReadOnlyAdmin:
    """Thin adapter; imports confluent-kafka only when instantiated."""

    def __init__(self, config: dict[str, Any]):
        from confluent_kafka.admin import AdminClient

        self._client = AdminClient(config)

    def inventory(self) -> dict[str, Any]:
        metadata = self._client.list_topics(timeout=10)
        return {
            "cluster_id": metadata.cluster_id,
            "controller_id": metadata.controller_id,
            "brokers": [{"id": b.id, "host": b.host, "port": b.port} for b in metadata.brokers.values()],
            "topics": [
                {
                    "name": name,
                    "partitions": [
                        {"partition": p.id, "leader": p.leader, "replicas": p.replicas, "isr": p.isrs}
                        for p in topic.partitions.values()
                    ],
                }
                for name, topic in metadata.topics.items()
            ],
        }
