from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DbtProject:
    tenant_id: str
    environment: str
    project_id: str
    project_name: str
    dbt_version: str
    artifact_schema_versions: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    latest_manifest_at: str | None = None
    latest_run_at: str | None = None
    health: dict[str, Any] = field(default_factory=dict)
    adapter_type: str = "unknown"
    repository: str = "unknown"
    default_branch: str = "unknown"
    schema_version: int = 1
