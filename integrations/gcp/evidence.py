from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from packages.collectors.sdk import EvidenceState, MetricObservation, ResourceObservation


def _seconds(value) -> int | None:
    if value is None:
        return None
    if hasattr(value, "total_seconds"):
        return int(value.total_seconds())
    seconds = getattr(value, "seconds", None)
    return int(seconds) if seconds is not None else None


def _name(resource_name: str) -> str:
    return resource_name.rsplit("/", 1)[-1]


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def envelope(context, project: str, kind: str, resource_id: str, name: str, fields: dict) -> dict:
    return {
        "tenant_id": context.tenant_id,
        "environment": context.attributes.get("environment", "default"),
        "messaging_system": "google_pubsub",
        "provider": "gcp",
        "provider_account_scope": project,
        "cloud_region_or_location": "",
        "resource_kind": kind,
        "provider_resource_id": resource_id,
        "name": name,
        "observed_at": datetime.now(timezone.utc),
        "data_status": "complete",
        "source_coverage": 1.0,
        "confidence": 1.0,
        "collection_method": "google_cloud_admin_read_api",
        "source_integration": context.integration_id,
        "schema_version": "1",
        "raw_message_payloads_read": False,
        **fields,
    }


def topic(context, project: str, item) -> ResourceObservation:
    resource_id = str(item.name)
    fields = {
        "message_retention_seconds": _seconds(getattr(item, "message_retention_duration", None)),
        "cmek_enabled": bool(getattr(item, "kms_key_name", "")),
        "schema_attached": bool(getattr(getattr(item, "schema_settings", None), "schema", "")),
        "message_transform_count": len(getattr(item, "message_transforms", ()) or ()),
        "ingestion_source_configured": getattr(item, "ingestion_data_source_settings", None) is not None,
    }
    env = envelope(context, project, "topic", resource_id, _name(resource_id), fields)
    return ResourceObservation(
        "gcp",
        project,
        "",
        "pubsub",
        "topic",
        resource_id,
        env["name"],
        env["observed_at"],
        context.collection_run_id,
        source_evidence=env,
        evidence_confidence=1.0,
    )


def delivery_type(item) -> str:
    for attr, kind in (
        ("push_config", "push"),
        ("bigquery_config", "bigquery"),
        ("cloud_storage_config", "cloud_storage"),
    ):
        value = getattr(item, attr, None)
        if value and bool(value):
            return kind
    return "pull"


def subscription(
    context, project: str, item, visible_topics: frozenset[str]
) -> tuple[ResourceObservation, ResourceObservation | None]:
    resource_id, topic_id = str(item.name), str(item.topic)
    dead_letter = getattr(item, "dead_letter_policy", None)
    dead_letter_topic = str(getattr(dead_letter, "dead_letter_topic", ""))
    raw_filter = str(getattr(item, "filter", ""))
    retry = getattr(item, "retry_policy", None)
    expiration = getattr(getattr(item, "expiration_policy", None), "ttl", None)
    fields = {
        "topic_resource_id": topic_id,
        "ack_deadline_seconds": getattr(item, "ack_deadline_seconds", None),
        "retain_acked_messages": bool(getattr(item, "retain_acked_messages", False)),
        "message_retention_seconds": _seconds(getattr(item, "message_retention_duration", None)),
        "expiration_seconds": _seconds(expiration),
        "exactly_once_delivery": bool(getattr(item, "enable_exactly_once_delivery", False)),
        "ordering_enabled": bool(getattr(item, "enable_message_ordering", False)),
        "delivery_type": delivery_type(item),
        "retry_policy_enabled": retry is not None,
        "retry_minimum_backoff_seconds": _seconds(getattr(retry, "minimum_backoff", None)),
        "retry_maximum_backoff_seconds": _seconds(getattr(retry, "maximum_backoff", None)),
        "dead_letter_topic_resource_id": dead_letter_topic or None,
        "maximum_delivery_attempts": getattr(dead_letter, "max_delivery_attempts", None),
        "filter_present": bool(raw_filter),
        "filter_fingerprint": _fingerprint(raw_filter) if raw_filter else None,
    }
    env = envelope(context, project, "subscription", resource_id, _name(resource_id), fields)
    resource = ResourceObservation(
        "gcp",
        project,
        "",
        "pubsub",
        "subscription",
        resource_id,
        env["name"],
        env["observed_at"],
        context.collection_run_id,
        source_evidence=env,
        evidence_confidence=1.0,
    )
    dlq = None
    if dead_letter_topic and dead_letter_topic in visible_topics:
        dlq_env = envelope(
            context,
            project,
            "dead_letter_topic",
            dead_letter_topic,
            _name(dead_letter_topic),
            {
                "source_subscription_resource_id": resource_id,
                "source_topic_resource_id": topic_id,
                "maximum_delivery_attempts": fields["maximum_delivery_attempts"],
            },
        )
        dlq = ResourceObservation(
            "gcp",
            project,
            "",
            "pubsub",
            "dead_letter_topic",
            dead_letter_topic,
            dlq_env["name"],
            dlq_env["observed_at"],
            context.collection_run_id,
            source_evidence=dlq_env,
            evidence_confidence=1.0,
        )
    return resource, dlq


def metric(
    resource: ResourceObservation,
    metric_name: str,
    value: float | None,
    metric_kind: str,
    period_seconds: int,
    *,
    region: str = "",
    scope: str = "regional",
) -> MetricObservation:
    state = EvidenceState.MEASURED if value is not None else EvidenceState.MISSING
    aggregation = "gauge" if metric_kind == "GAUGE" else "delta_window"
    return MetricObservation(
        resource.canonical_id,
        metric_name,
        value,
        state,
        "provider_native",
        aggregation,
        period_seconds,
        resource.observed_at,
        "gcp",
        {"region": region, "measurement_scope": scope, "metric_kind": metric_kind},
    )
