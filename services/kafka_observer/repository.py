from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from elasticsearch import Elasticsearch


class ObserverRepository(Protocol):
    def load_checkpoint(self, provider: str) -> dict[str, Any] | None: ...
    def save_checkpoint(self, provider: str, checkpoint: dict[str, Any]) -> None: ...
    def save_collection(self, provider: str, inventory: dict[str, Any], checkpoint: dict[str, Any]) -> None: ...
    def save_error(self, error: dict[str, Any]) -> None: ...
    def save_connector_projection(self, payload: dict[str, Any]) -> None: ...
    def save_schema_projection(self, payload: dict[str, Any]) -> None: ...


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
        now = datetime.now(timezone.utc).isoformat()
        return {
            "tenant_id": self.tenant_id,
            "environment": self.environment,
            "integration_id": self.integration_id,
            "schema_version": "1.0",
            "observed_at": now,
            "updated_at": now,
        }

    def load_checkpoint(self, provider: str) -> dict[str, Any] | None:
        response = self.es.get(index="dataobs-kafka-observer-checkpoints-v1-read", id=self._id(provider), ignore=[404])
        if not response.get("found"):
            return None
        source = response.get("_source", {})
        return source.get("document", source)

    def save_checkpoint(self, provider: str, checkpoint: dict[str, Any]) -> None:
        self.es.index(
            index="dataobs-kafka-observer-checkpoints-v1-write",
            id=self._id(provider),
            document=self._base() | {"id": provider, **checkpoint},
            refresh="wait_for",
        )

    def save_error(self, error: dict[str, Any]) -> None:
        self.es.index(
            index="logs-dataobs.kafka-collection-error-default",
            id=self._id(error["collector"], error["fingerprint"]),
            document=self._base() | {"@timestamp": error["last_observed"], **error},
        )

    def save_connector_projection(self, payload: dict[str, Any]) -> None:
        """Persist bounded, credential-free current connector projections."""
        cluster_id = str(payload.get("cluster_id") or self.integration_id)
        status = payload.get("data_status", "unknown")
        for connector in payload.get("connectors", [])[:1000]:
            state = str(connector.get("state") or "UNKNOWN").upper()
            failed = connector.get("failed_task_count")
            if state == "FAILED":
                health, reasons = "critical", ["connector_failed"]
            elif isinstance(failed, int) and failed > 0:
                health, reasons = "degraded", ["failed_tasks_observed"]
            elif state == "PAUSED":
                health, reasons = "warning", ["connector_paused"]
            elif state == "RUNNING" and failed == 0:
                health, reasons = "healthy", ["connector_running", "failed_tasks_zero"]
            else:
                health, reasons = "unknown", ["connector_state_unknown"]
            observed = connector.get("observed_at") or datetime.now(timezone.utc).isoformat()
            safe = {
                key: connector.get(key)
                for key in (
                    "connector_id",
                    "name",
                    "connector_type",
                    "classification",
                    "state",
                    "task_count",
                    "failed_task_count",
                    "task_states",
                    "worker_ids",
                    "class_fingerprint",
                    "config_fingerprint",
                )
                if key in connector
            }
            safe.update(
                {
                    "@timestamp": observed,
                    "observed_at": observed,
                    "cluster_id": cluster_id,
                    "health": health,
                    "reason_codes": reasons,
                    "worker_count": len(connector.get("worker_ids", [])) if "worker_ids" in connector else None,
                    "source_coverage": ["kafka_connect"],
                    "data_status": status,
                }
            )
            self.es.index(
                index="dataobs-kafka-connectors-v1-write",
                id=self._id(cluster_id, safe["connector_id"]),
                document=self._base() | safe,
            )

    def save_schema_projection(self, payload: dict[str, Any]) -> None:
        """Persist one bounded subject summary; raw schema definitions never cross this boundary."""
        cluster_id = str(payload.get("cluster_id") or payload.get("registry_id") or self.integration_id)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in payload.get("schemas", [])[:100_000]:
            grouped.setdefault(str(row["subject_id"]), []).append(row)
        for subject_id, rows in grouped.items():
            rows = sorted(rows, key=lambda row: int(row.get("version", 0)), reverse=True)[:100]
            latest = rows[0]
            observed = max(
                (str(row["observed_at"]) for row in rows if row.get("observed_at")),
                default=datetime.now(timezone.utc).isoformat(),
            )
            versions = [
                {
                    key: row.get(key)
                    for key in ("version", "schema_id", "schema_type", "fingerprint", "semantic_summary", "observed_at")
                }
                | {"reference_count": len(row.get("references", []))}
                for row in rows
            ]
            document = self._base() | {
                "@timestamp": observed,
                "observed_at": observed,
                "cluster_id": cluster_id,
                "subject_id": subject_id,
                "subject": latest.get("subject", subject_id),
                "name": subject_id,
                "schema_type": latest.get("schema_type"),
                "compatibility": latest.get("compatibility_mode"),
                "latest_version": latest.get("version"),
                "versions": versions,
                "fingerprints": [row.get("fingerprint") for row in rows],
                "references": latest.get("references", []),
                "semantic_summary": latest.get("semantic_summary"),
                "health": "unknown" if latest.get("compatibility_mode") == "UNKNOWN" else "healthy",
                "reason_codes": (
                    ["compatibility_unknown"]
                    if latest.get("compatibility_mode") == "UNKNOWN"
                    else ["registry_observed"]
                ),
                "source_coverage": ["schema_registry"],
                "data_status": payload.get("data_status", "unknown"),
            }
            self.es.index(
                index="dataobs-kafka-schemas-v1-write", id=self._id(cluster_id, subject_id), document=document
            )

    def acquire_lease(self, name: str, owner: str, expires_at: str) -> bool:
        lease_id = self._id(name)
        script = {
            "source": "if (ctx._source.lease_owner == params.owner) { ctx._source.lease_expires_at=params.expires; ctx._source.renewed_at=params.now; } else if (ctx._source.lease_expires_at.compareTo(params.now) <= 0) { ctx._source.lease_owner=params.owner; ctx._source.lease_expires_at=params.expires; ctx._source.fencing_token=(ctx._source.fencing_token ?: 0)+1; ctx._source.renewed_at=params.now; } else { ctx.op='none'; }",
            "params": {"owner": owner, "expires": expires_at, "now": datetime.now(timezone.utc).isoformat()},
        }
        response = self.es.update(
            index="dataobs-kafka-observer-leases-v1-write",
            id=lease_id,
            script=script,
            upsert=self._base() | {"lease_owner": owner, "lease_expires_at": expires_at, "fencing_token": 1},
            refresh="wait_for",
        )
        return response.get("result") != "noop"

    def release_lease(self, name: str, owner: str) -> None:
        self.es.update(
            index="dataobs-kafka-observer-leases-v1-write",
            id=self._id(name),
            script={
                "source": "if (ctx._source.lease_owner == params.owner) { ctx.op='delete' }",
                "params": {"owner": owner},
            },
        )

    def save_collection(self, provider: str, inventory: dict[str, Any], checkpoint: dict[str, Any]) -> None:
        now = inventory.get("observed_at") or datetime.now(timezone.utc).isoformat()
        base = self._base()
        cluster_id = inventory["cluster_id"]
        topics = inventory.get("topics", [])
        groups = inventory.get("consumer_groups", [])
        cluster = base | {
            "@timestamp": now,
            "cluster_id": cluster_id,
            "controller_id": inventory.get("controller_id"),
            "broker_count": len(inventory.get("brokers", [])),
            "topic_count": len(topics),
            "consumer_group_count": len(groups),
            "health": "degraded" if inventory.get("warnings") else "healthy",
            "reason_codes": inventory.get("warnings", []),
            "source_coverage": inventory.get("source_coverage", ["kafka_admin"]),
            "name": cluster_id,
        }
        self.es.index(
            index="logs-dataobs.kafka_inventory-default",
            document=cluster | {"event_type": "inventory"},
        )
        self.es.index(
            index="dataobs-kafka-clusters-v1-write",
            id=self._id(cluster_id),
            document=cluster,
        )
        for broker in inventory.get("brokers", []):
            broker_id = str(broker["id"])
            broker_doc = base | {
                "@timestamp": now,
                "cluster_id": cluster_id,
                "broker_id": broker_id,
                "host": broker.get("host"),
                "port": broker.get("port"),
                "rack": broker.get("rack"),
                "controller": broker.get("id") == inventory.get("controller_id"),
                "health": "healthy",
                "name": broker_id,
            }
            self.es.index(
                index="dataobs-kafka-brokers-v1-write",
                id=self._id(cluster_id, broker_id),
                document=broker_doc,
            )
        for topic in inventory.get("topics", []):
            topic_id = topic.get("id") or topic["name"]
            config = topic.get("config", {})
            unhealthy = any(
                not p.get("leader_available", True) or set(p.get("replicas", [])) - set(p.get("isr", []))
                for p in topic.get("partitions", [])
            )
            topic_doc = base | {
                "@timestamp": now,
                "stream_id": str(topic_id),
                "cluster_id": cluster_id,
                "topic_id": str(topic_id),
                "topic": topic["name"],
                "name": topic["name"],
                "partition_count": topic.get("partition_count"),
                "replication_factor": topic.get("replication_factor"),
                "cleanup_policy": config.get("cleanup.policy"),
                "retention_ms": _integer(config.get("retention.ms")),
                "retention_bytes": _integer(config.get("retention.bytes")),
                "min_insync_replicas": _integer(config.get("min.insync.replicas")),
                "health": "degraded" if unhealthy else "healthy",
                "reason_codes": ["replication_unhealthy"] if unhealthy else [],
            }
            self.es.index(
                index="dataobs-kafka-topics-v1-write",
                id=self._id(cluster_id, topic_id),
                document=topic_doc,
            )
            for partition in topic.get("partitions", []):
                missing = sorted(set(partition.get("replicas", [])) - set(partition.get("isr", [])))
                leader = partition.get("leader")
                self.es.index(
                    index="dataobs-kafka-partitions-v1-write",
                    id=self._id(cluster_id, topic_id, partition["partition"]),
                    document=base
                    | {
                        "@timestamp": now,
                        "cluster_id": cluster_id,
                        "topic_id": str(topic_id),
                        "partition_id": str(partition["partition"]),
                        "leader_id": leader,
                        "replicas": partition.get("replicas", []),
                        "isr": partition.get("isr", []),
                        "offline_replicas": missing,
                        "under_replicated": bool(missing),
                        "leader_available": leader is not None and leader >= 0,
                        "health": (
                            "offline" if leader is None or leader < 0 else "under_replicated" if missing else "healthy"
                        ),
                    },
                )
        for group in inventory.get("consumer_groups", []):
            group_id = group["group_id"]
            self.es.index(
                index="dataobs-kafka-consumer-groups-v1-write",
                id=self._id(cluster_id, group_id),
                document=base
                | {
                    "@timestamp": now,
                    "cluster_id": cluster_id,
                    "consumer_group_id": group_id,
                    "group_id": group_id,
                    "name": group_id,
                    "state": group.get("state"),
                    "protocol": group.get("protocol"),
                    "coordinator": group.get("coordinator"),
                    "members": group.get("members", [])[:1000],
                    "assignments": [a for m in group.get("members", [])[:1000] for a in m.get("assignments", [])][
                        :10000
                    ],
                },
            )
        self.es.index(
            index="dataobs-kafka-observer-checkpoints-v1-write",
            id=self._id(provider),
            document=base | {"id": provider, **checkpoint},
            refresh="wait_for",
        )


class MemoryObserverRepository:
    """Test-only repository."""

    def __init__(self):
        self.checkpoints: dict[str, dict[str, Any]] = {}
        self.collections: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []

    def load_checkpoint(self, provider: str) -> dict[str, Any] | None:
        return self.checkpoints.get(provider)

    def save_checkpoint(self, provider: str, checkpoint: dict[str, Any]) -> None:
        self.checkpoints[provider] = dict(checkpoint)

    def save_collection(self, provider: str, inventory: dict[str, Any], checkpoint: dict[str, Any]) -> None:
        self.collections.append(inventory)
        self.checkpoints[provider] = checkpoint

    def save_error(self, error: dict[str, Any]) -> None:
        self.errors.append(dict(error))

    def save_connector_projection(self, payload: dict[str, Any]) -> None:
        self.collections.append({"capability": "connectors", **payload})

    def save_schema_projection(self, payload: dict[str, Any]) -> None:
        self.collections.append({"capability": "schemas", **payload})


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
