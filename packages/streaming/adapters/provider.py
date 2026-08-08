"""Provider observation adapters for the canonical messaging contract.

Adapters consume already-collected metadata/aggregate telemetry.  They never call
broker APIs and intentionally copy only allowlisted fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..contracts import (
    DataStatus,
    MeasurementMethod,
    MessagingBacklog,
    MessagingResource,
    MessagingSystem,
    ResourceKind,
)
from ..identity import canonical_messaging_id


class ProviderAdapter:
    system: MessagingSystem
    provider: str
    resource_kinds: frozenset[ResourceKind]

    def canonical_id(self, observation: dict[str, Any]) -> str:
        return canonical_messaging_id(
            tenant_id=str(observation["tenant_id"]),
            environment=str(observation["environment"]),
            messaging_system=self.system.value,
            provider_account_scope=str(observation["provider_account_scope"]),
            region_or_location=str(observation.get("cloud_region_or_location", "")),
            namespace=str(observation.get("namespace", "")),
            resource_kind=str(observation["resource_kind"]),
            provider_resource_id=str(observation["provider_resource_id"]),
        )

    def resource(self, observation: dict[str, Any]) -> MessagingResource:
        kind = ResourceKind(observation["resource_kind"])
        if kind not in self.resource_kinds:
            raise ValueError(f"{kind.value} is not valid for {self.system.value}")
        canonical_id = self.canonical_id(observation)
        return MessagingResource(
            id=canonical_id,
            canonical_resource_id=canonical_id,
            tenant_id=observation["tenant_id"],
            environment=observation["environment"],
            messaging_system=self.system,
            provider=self.provider,
            provider_account_scope=observation["provider_account_scope"],
            cloud_region_or_location=observation.get("cloud_region_or_location", ""),
            resource_kind=kind,
            provider_resource_id=observation["provider_resource_id"],
            name=observation["name"],
            namespace_id=observation.get("namespace_id"),
            parent_resource_id=observation.get("parent_resource_id"),
            observed_at=observation["observed_at"],
            data_status=DataStatus(observation.get("data_status", "partial")),
            confidence=observation.get("confidence", 0),
            source_coverage=observation.get("source_coverage", 0),
        )

    def backlog(
        self,
        observation: dict[str, Any],
        *,
        approximate: bool = False,
        provider_metric: str | None = None,
    ) -> MessagingBacklog:
        """Normalize counts without converting absent fields to zero."""
        resource_id = self.canonical_id(observation)
        return MessagingBacklog(
            id=f"{resource_id}:backlog:{observation['observed_at']}",
            resource_id=resource_id,
            subscription_id=observation.get("subscription_id"),
            tenant_id=observation["tenant_id"],
            environment=observation["environment"],
            messaging_system=self.system,
            observed_at=observation["observed_at"],
            data_status=DataStatus(observation.get("data_status", "partial")),
            confidence=observation.get("confidence", 0),
            source_coverage=observation.get("source_coverage", 0),
            backlog_messages=observation.get("backlog_messages"),
            backlog_bytes=observation.get("backlog_bytes"),
            backlog_age_seconds=observation.get("backlog_age_seconds"),
            inflight_messages=observation.get("inflight_messages"),
            delayed_messages=observation.get("delayed_messages"),
            unacknowledged_messages=observation.get("unacknowledged_messages"),
            provider_metric=provider_metric,
            measurement_method=(
                MeasurementMethod.PROVIDER_APPROXIMATE if approximate else MeasurementMethod.PROVIDER_MEASURED
            ),
            missing_inputs=list(observation.get("missing_inputs", [])),
        )


def require_observation_envelope(observation: dict[str, Any]) -> None:
    required = {
        "tenant_id",
        "environment",
        "provider_account_scope",
        "resource_kind",
        "provider_resource_id",
        "name",
        "observed_at",
    }
    missing = sorted(required - observation.keys())
    if missing:
        raise ValueError(f"observation envelope missing: {', '.join(missing)}")
    if not isinstance(observation["observed_at"], datetime):
        raise ValueError("observed_at must be a datetime")
