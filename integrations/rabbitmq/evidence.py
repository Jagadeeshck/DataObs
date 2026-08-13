from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import quote

from packages.collectors.sdk import EvidenceState, HealthObservation, MetricObservation, ResourceObservation

LIMITATIONS = (
    "Management HTTP API current inventory and aggregate counters only; no Prometheus history",
    "No messages, connections, channels, consumers, user identities, or arbitrary arguments are collected",
    "DLQ queues are classified only when observed bindings prove the destination",
    "Hosted RabbitMQ 4.3.x validation remains required",
)


def fingerprint(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def account_scope(context) -> str:
    return f"rabbitmq:{fingerprint(context.integration_id)[:24]}"


def native_id(vhost: str, kind: str, name: str) -> str:
    return f"rabbitmq://{quote(vhost, safe='')}/{kind}/{quote(name, safe='')}"


def envelope(context, kind, native, name, vhost, fields, *, partial=False):
    observed = datetime.now(timezone.utc)
    return {
        "tenant_id": context.tenant_id,
        "environment": context.attributes.get("environment", "default"),
        "messaging_system": "rabbitmq",
        "provider": "rabbitmq",
        "provider_account_scope": account_scope(context),
        "cloud_region_or_location": "",
        "resource_kind": kind,
        "provider_resource_id": native,
        "name": name,
        "namespace": vhost,
        "observed_at": observed,
        "data_status": "partial" if partial else "complete",
        "source_coverage": 0.8 if partial else 1.0,
        "confidence": 1.0,
        "collection_method": "rabbitmq_management_http_api",
        "source_integration": context.integration_id,
        "schema_version": "1",
        **fields,
    }


def resource(context, kind, name, vhost, fields, *, partial=False):
    native = native_id(vhost, kind, name)
    env = envelope(context, kind, native, name, vhost, fields, partial=partial)
    return ResourceObservation(
        "rabbitmq",
        account_scope(context),
        "",
        "messaging",
        kind,
        native,
        name,
        env["observed_at"],
        context.collection_run_id,
        source_evidence=env,
        evidence_confidence=env["confidence"],
    )


def metric(resource_observation, name, value, unit="count", aggregation="gauge"):
    return MetricObservation(
        resource_observation.canonical_id,
        name,
        value,
        EvidenceState.MEASURED if value is not None else EvidenceState.MISSING,
        unit,
        aggregation,
        0,
        resource_observation.observed_at,
        "rabbitmq",
    )


def health(context, available, reason):
    return HealthObservation(
        f"{account_scope(context)}:cluster",
        "available" if available else "unavailable",
        reason,
        EvidenceState.MEASURED,
        "info" if available else "critical",
        datetime.now(timezone.utc),
    )
