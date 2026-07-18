from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KibanaAuth:
    base_url: str
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    space: str = "default"


@dataclass(frozen=True)
class WorkflowPlanItem:
    workflow_id: str
    path: str
    checksum: str
    action: str
