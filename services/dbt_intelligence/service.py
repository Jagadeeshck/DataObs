"""Artifact ingestion orchestration; no dbt or warehouse execution occurs here."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from hashlib import sha256
from typing import Any

from integrations.dbt.contracts import DbtArtifactEnvelope, NormalizedArtifact
from integrations.dbt.normalizer import parse_artifact
from integrations.dbt.safety import ArtifactLimits

from .health import project_health
from .models import DbtProject
from .repository import DbtIntelligenceRepository


class DbtIntelligenceService:
    def __init__(self, repository: DbtIntelligenceRepository, limits: ArtifactLimits | None = None) -> None:
        self.repository, self.limits = repository, limits or ArtifactLimits()

    def ingest(self, trusted_tenant: str, trusted_environment: str, project_id: str, project_name: str, artifact_type: str, document: dict[str, Any], source: str = "api", repository_ref: str = "unknown", commit_sha: str = "unknown") -> dict[str, Any]:
        envelope = DbtArtifactEnvelope(trusted_tenant, trusted_environment, project_id, project_name, artifact_type, "", "", source=source, repository_ref=repository_ref, commit_sha=commit_sha)  # type: ignore[arg-type]
        artifact = parse_artifact(document, envelope, self.limits)
        event_id = sha256("\x1f".join((trusted_tenant, trusted_environment, project_id, artifact_type, artifact.envelope.artifact_schema_version, artifact.envelope.invocation_id, artifact.envelope.artifact_fingerprint)).encode()).hexdigest()
        created = self.repository.append_artifact_event(event_id, {"event_id": event_id, "envelope": asdict(artifact.envelope)})
        if created: self._project(artifact)
        return {"event_id": event_id, "status": "created" if created else "replayed", "artifact": artifact}

    def _project(self, artifact: NormalizedArtifact) -> None:
        envelope = artifact.envelope
        existing = getattr(self.repository, "get_project", lambda *_: None)(envelope.tenant_id, envelope.environment, envelope.project_id) or {}
        for resource in artifact.resources: self.repository.upsert_resource_projection(envelope.tenant_id, envelope.environment, envelope.project_id, resource)
        counts = dict(existing.get("counts", {}))
        if artifact.resources: counts = dict(Counter(item["resource_type"] for item in artifact.resources))
        versions = dict(existing.get("artifact_schema_versions", {})); versions[envelope.artifact_type] = envelope.artifact_schema_version
        health = existing.get("health") or project_health({})
        self.repository.upsert_project(DbtProject(envelope.tenant_id, envelope.environment, envelope.project_id, envelope.project_name, envelope.dbt_version, versions, counts, envelope.generated_at if envelope.artifact_type == "manifest" else existing.get("latest_manifest_at"), envelope.generated_at if envelope.artifact_type == "run_results" else existing.get("latest_run_at"), health, repository=envelope.repository_ref))
