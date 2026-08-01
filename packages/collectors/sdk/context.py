from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class IntegrationContext:
    """Trusted runtime identity; provider configuration cannot override these values."""

    tenant_id: str
    integration_id: str
    collection_run_id: str
    deadline: datetime
    trace_id: str | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.integration_id or not self.collection_run_id:
            raise ValueError("tenant_id, integration_id and collection_run_id are required")
        if self.deadline.tzinfo is None:
            raise ValueError("deadline must be timezone-aware")

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, (self.deadline - datetime.now(timezone.utc)).total_seconds())
