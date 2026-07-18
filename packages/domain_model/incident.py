from datetime import datetime
from typing import Any, Dict, List

from .base import ProductEntity


class Incident(ProductEntity):
    incident_state: str = "open"
    severity: str = "medium"
    affected_assets: List[str] = []
    root_cause_candidate: str | None = None
    business_impact: str | None = None
    evidence: List[Dict[str, Any]] = []
    deduplication_key: str
    workflow_ref: str | None = None
    opened_at: datetime | None = None
    resolved_at: datetime | None = None
