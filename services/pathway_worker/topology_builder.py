from __future__ import annotations

from typing import Any

from packages.pathways.intelligence import canonical_edge, canonical_node


def projections_from_span(
    span: dict[str, Any], tenant: str, environment: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    service_name = span.get("service.name") or "unknown"
    topic_name = span.get("messaging.destination.name") or "unknown"
    cluster = span.get("messaging.kafka.cluster.id") or span.get("messaging.cluster.id")
    observed = span.get("@timestamp") or span.get("timestamp")
    evidence_ref = span.get("_source_document_id")
    service = canonical_node(
        tenant,
        environment,
        "service",
        service_name,
        qualified_name=f"{span.get('service.namespace', '')}/{service_name}",
        platform="opentelemetry",
        first_seen=observed,
        last_seen=observed,
        source_coverage=["trace_observed"],
        evidence_refs=[evidence_ref],
    )
    topic = canonical_node(
        tenant,
        environment,
        "kafka_topic",
        topic_name,
        qualified_name=f"kafka://{cluster or 'unknown'}/{topic_name}",
        platform="kafka",
        cluster_id=cluster,
        first_seen=observed,
        last_seen=observed,
        source_coverage=["trace_observed"],
        evidence_refs=[evidence_ref],
    )
    operation = span.get("messaging.operation.type", "unknown")
    if operation in {"send", "publish"}:
        source, destination, kind = service, topic, "producer_to_topic"
    elif operation in {"receive", "process", "consume"}:
        source, destination, kind = topic, service, "topic_to_consumer"
    else:
        source, destination, kind = topic, service, "partial_edge"
    edge = canonical_edge(
        tenant,
        environment,
        source["node_id"],
        destination["node_id"],
        kind,
        messaging_system="kafka",
        cluster_id=cluster,
        topic_id=topic["node_id"],
        consumer_group_id=span.get("messaging.consumer.group.name"),
        first_seen=observed,
        last_seen=observed,
        evidence_type="trace_observed" if span.get("trace_id") else "unknown",
        coverage="complete" if span.get("trace_id") and kind != "partial_edge" else "partial",
        evidence_refs=[evidence_ref],
    )
    edge["source_document_ref"] = evidence_ref
    return [service, topic], edge


def edge_from_span(span: dict[str, Any], tenant: str, environment: str) -> dict[str, Any]:
    return projections_from_span(span, tenant, environment)[1]
