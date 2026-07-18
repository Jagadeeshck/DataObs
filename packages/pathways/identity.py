from __future__ import annotations

from packages.domain_model.identity import deterministic_id


def cluster_id(tenant: str, environment: str, integration: str, kafka_cluster_id: str) -> str:
    return deterministic_id("kcluster", [tenant, environment, integration, kafka_cluster_id])


def topic_id(tenant: str, environment: str, kafka_cluster_id: str, topic: str) -> str:
    return deterministic_id("ktopic", [tenant, environment, kafka_cluster_id, topic])


def partition_id(topic: str, partition: int) -> str:
    return deterministic_id("kpartition", [topic, str(partition)])


def consumer_group_id(tenant: str, environment: str, kafka_cluster_id: str, group: str) -> str:
    return deterministic_id("kgroup", [tenant, environment, kafka_cluster_id, group])


def node_id(tenant: str, environment: str, node_type: str, namespace: str, name: str) -> str:
    return deterministic_id("pnode", [tenant, environment, node_type, namespace, name])


def edge_id(
    tenant: str, environment: str, source: str, destination: str, system: str, topic: str = "", group: str = ""
) -> str:
    return deterministic_id("pedge", [tenant, environment, source, destination, system, topic, group])


def pathway_id(edges: list[str]) -> str:
    return deterministic_id("pathway", edges)
