from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from elasticsearch import Elasticsearch


class ObserverRepository(Protocol):
    def load_checkpoint(self, provider: str) -> dict[str, Any] | None: ...
    def save_collection(self, provider: str, inventory: dict[str, Any], checkpoint: dict[str, Any]) -> None: ...


class ElasticsearchObserverRepository:
    """Durable Observer product store.

    Document identifiers include the tenant and environment.  Inventory events are
    append-only while aliases hold the latest projections.  Kafka payloads are
    intentionally not accepted by this boundary.
    """

    def __init__(self, es: Elasticsearch, tenant_id: str, environment: str, integration_id: str):
        self.es = es
        self.tenant_id = tenant_id
        self.environment = environment
        self.integration_id = integration_id

    def _id(self, *parts: object) -> str:
        return ":".join([self.tenant_id, self.environment, *(str(p) for p in parts)])

    def _base(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "environment": self.environment,
            "integration_id": self.integration_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def load_checkpoint(self, provider: str) -> dict[str, Any] | None:
        response = self.es.get(index="dataobs-pathway-checkpoints-v1-read", id=self._id(provider), ignore=[404])
        return response.get("_source", {}).get("document") if response.get("found") else None

    def save_collection(self, provider: str, inventory: dict[str, Any], checkpoint: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        base = self._base()
        cluster_id = inventory["cluster_id"]
        self.es.index(
            index="logs-dataobs.kafka_inventory-default",
            document=base
            | {"@timestamp": now, "event_type": "inventory", "cluster_id": cluster_id, "document": inventory},
        )
        self.es.index(
            index="dataobs-kafka-clusters-v1-write",
            id=self._id(cluster_id),
            document=base | {"cluster_id": cluster_id, "document": inventory},
        )
        for broker in inventory.get("brokers", []):
            self.es.index(
                index="dataobs-kafka-brokers-v1-write",
                id=self._id(cluster_id, broker["id"]),
                document=base | {"cluster_id": cluster_id, "broker_id": str(broker["id"]), "document": broker},
            )
        for topic in inventory.get("topics", []):
            topic_id = topic.get("id") or topic["name"]
            self.es.index(
                index="dataobs-kafka-topics-v1-write",
                id=self._id(cluster_id, topic_id),
                document=base
                | {"cluster_id": cluster_id, "topic_id": str(topic_id), "name": topic["name"], "document": topic},
            )
            for partition in topic.get("partitions", []):
                self.es.index(
                    index="dataobs-kafka-partitions-v1-write",
                    id=self._id(cluster_id, topic_id, partition["partition"]),
                    document=base
                    | {
                        "cluster_id": cluster_id,
                        "topic_id": str(topic_id),
                        "partition_id": str(partition["partition"]),
                        "document": partition,
                    },
                )
        for group in inventory.get("consumer_groups", []):
            self.es.index(
                index="dataobs-kafka-consumer-groups-v1-write",
                id=self._id(cluster_id, group["group_id"]),
                document=base | {"cluster_id": cluster_id, "consumer_group_id": group["group_id"], "document": group},
            )
        self.es.index(
            index="dataobs-pathway-checkpoints-v1-write",
            id=self._id(provider),
            document=base | {"id": provider, "document": checkpoint},
            refresh="wait_for",
        )


class MemoryObserverRepository:
    """Test-only repository."""

    def __init__(self):
        self.checkpoints: dict[str, dict[str, Any]] = {}
        self.collections: list[dict[str, Any]] = []

    def load_checkpoint(self, provider: str) -> dict[str, Any] | None:
        return self.checkpoints.get(provider)

    def save_collection(self, provider: str, inventory: dict[str, Any], checkpoint: dict[str, Any]) -> None:
        self.collections.append(inventory)
        self.checkpoints[provider] = checkpoint
