from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    STALE = "stale"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class StreamEnvelope(BaseModel):
    data_status: DataStatus
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_coverage: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    request_id: str
    trace_id: str | None = None


def envelope(request_id: str, *, configured: bool, found: bool, sources: list[str] | None = None) -> dict[str, Any]:
    if not configured:
        status = DataStatus.NOT_CONFIGURED
    elif not found:
        status = DataStatus.UNKNOWN
    else:
        status = DataStatus.COMPLETE
    return StreamEnvelope(
        data_status=status,
        request_id=request_id,
        source_coverage=sources or [],
        confidence=1.0 if found else None,
        warnings=[] if found else ["No measured evidence is available"],
        missing_inputs=[] if found else ["observer_projection"],
    ).model_dump(mode="json")
