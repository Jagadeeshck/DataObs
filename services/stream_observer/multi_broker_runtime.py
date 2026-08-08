from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from packages.streaming.adapters import ADAPTERS
from packages.streaming.adapters.provider import require_observation_envelope

from .repository import MessagingRepository


@dataclass(frozen=True)
class RuntimeCycleResult:
    read: int
    normalized: int
    rejected: int
    projected: int
    duplicates: int


class MultiBrokerRuntime:
    """Runs inside an existing leased worker; scheduling and lease ownership stay external."""

    def __init__(self, repository: MessagingRepository):
        self.repository = repository

    def run(
        self, observations: Iterable[dict[str, Any]], *, tenant_id: str, environment: str, fencing_token: int
    ) -> RuntimeCycleResult:
        counts = {"read": 0, "normalized": 0, "rejected": 0, "projected": 0, "duplicates": 0}
        for raw in observations:
            counts["read"] += 1
            if raw.get("tenant_id") != tenant_id or raw.get("environment") != environment:
                counts["rejected"] += 1
                continue
            try:
                require_observation_envelope(raw)
                system = str(raw["messaging_system"])
                adapter = ADAPTERS[system]()
                resource = adapter.resource(raw)
                document = resource.model_dump(mode="json") | {
                    "resource_id": resource.canonical_resource_id,
                    "region_or_location": resource.cloud_region_or_location,
                    "cloud": raw.get("cloud", ""),
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "measurement_method": raw.get("measurement_method", "provider_measured"),
                    "collection_method": raw["collection_method"],
                    "source_integration": raw["source_integration"],
                    "schema_version": "v1",
                    "metric_family": "resource",
                }
                counts["normalized"] += 1
                if not self.repository.append("resource", document):
                    counts["duplicates"] += 1
                self.repository.project("resource", document, fencing_token=fencing_token)
                counts["projected"] += 1
            except (KeyError, TypeError, ValueError):
                counts["rejected"] += 1
        return RuntimeCycleResult(**counts)
