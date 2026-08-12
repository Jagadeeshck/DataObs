"""Typed contracts for safe dbt artifact ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ArtifactType = Literal["manifest", "run_results", "catalog", "freshness"]


@dataclass(frozen=True)
class DbtArtifactEnvelope:
    tenant_id: str
    environment: str
    project_id: str
    project_name: str
    artifact_type: ArtifactType
    artifact_schema_version: str
    dbt_version: str
    invocation_id: str = "unknown"
    generated_at: str | None = None
    repository_ref: str = "unknown"
    commit_sha: str = "unknown"
    artifact_fingerprint: str = ""
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "api"
    schema_version: int = 1


@dataclass(frozen=True)
class NormalizedArtifact:
    envelope: DbtArtifactEnvelope
    resources: tuple[dict[str, Any], ...] = ()
    executions: tuple[dict[str, Any], ...] = ()
    freshness: tuple[dict[str, Any], ...] = ()
    catalog: tuple[dict[str, Any], ...] = ()
