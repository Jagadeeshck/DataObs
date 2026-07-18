from datetime import datetime
from typing import Any, Dict, List

from .base import ProductEntity


class WorkflowExecution(ProductEntity):
    workflow_id: str
    trigger: str
    workflow_status: str = "running"
    steps: List[Dict[str, Any]] = []
    approvals: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    started_at: datetime | None = None
    ended_at: datetime | None = None
    incident_ref: str | None = None
