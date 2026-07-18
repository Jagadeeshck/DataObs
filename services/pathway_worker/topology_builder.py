from __future__ import annotations

from packages.pathways.identity import edge_id, node_id


def edge_from_span(span: dict, tenant: str, environment: str) -> dict:
    service = node_id(
        tenant, environment, "service", span.get("service.namespace", ""), span.get("service.name", "unknown")
    )
    topic = node_id(
        tenant,
        environment,
        "topic",
        span.get("messaging.system", "kafka"),
        span.get("messaging.destination.name", "unknown"),
    )
    operation = span.get("messaging.operation.type", "unknown")
    if operation in {"send", "publish"}:
        source, destination, kind = service, topic, "producer_to_topic"
    else:
        source, destination, kind = topic, service, "topic_to_consumer"
    return {
        "id": edge_id(
            tenant,
            environment,
            source,
            destination,
            "kafka",
            span.get("messaging.destination.name", ""),
            span.get("messaging.consumer.group.name", ""),
        ),
        "source_node_id": source,
        "destination_node_id": destination,
        "edge_type": kind,
        "pathway_type": "edge" if span.get("trace_id") else "partial_edge",
        "confidence": 0.95 if span.get("trace_id") else 0.5,
    }
