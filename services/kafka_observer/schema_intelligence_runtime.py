"""Fenced, persistence-ordered streaming schema intelligence runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable

from packages.streaming.schema_intelligence import (
    CompatibilityEvaluation,
    SchemaApplicationBinding,
    SchemaIdentity,
    SchemaResourceBinding,
    evaluate_consumer_exposure,
)
from services.kafka_observer.intelligence_repository import canonical_id
from services.kafka_observer.schema_intelligence_repository import (
    BINDINGS,
    CHANGE_EVENTS,
    COMPATIBILITY_EVENTS,
    IMPACT_EVENTS,
    IMPACTS,
    SUBJECTS,
    VERSION_EVENTS,
    VERSIONS,
)


@dataclass(frozen=True)
class SchemaVersionObservation:
    identity: SchemaIdentity
    integration_id: str
    schema_version: int
    schema_id: str
    schema_type: str
    schema_fingerprint: str
    structural_fingerprint: str
    compatibility_mode: str
    observed_at: datetime
    evaluation: CompatibilityEvaluation
    reference_count: int = 0
    field_count: int = 0
    resource_binding: SchemaResourceBinding | None = None
    application_bindings: tuple[SchemaApplicationBinding, ...] = ()
    runtime_schema_errors: dict[str, int] | None = None


class SchemaIntelligenceRuntime:
    """Reconciles bounded observations; checkpoint advancement is always last."""

    MAX_BATCH = 200

    def __init__(
        self, repository: object, collector: Callable[..., Iterable[SchemaVersionObservation]], worker_id: str
    ):
        self.repository, self.collector, self.worker_id = repository, collector, worker_id

    def run_once(
        self, tenant: str, environment: str, cursor: str = "", *, limit: int = MAX_BATCH, now: datetime | None = None
    ) -> list[str]:
        now = now or datetime.now(timezone.utc)
        token = self.repository.acquire_lease(tenant, environment, self.worker_id, now + timedelta(seconds=90))
        if token is None:
            return []
        completed: list[str] = []
        observations = self.collector(tenant, environment, cursor, min(max(limit, 1), self.MAX_BATCH))
        for observation in observations:
            if observation.identity.tenant_id != tenant or observation.identity.environment != environment:
                raise ValueError("collector isolation violation")
            event_id = canonical_id(
                "schema-version",
                tenant,
                environment,
                observation.identity.registry_id,
                observation.identity.subject_id,
                observation.schema_version,
                observation.schema_fingerprint,
            )
            base = self._version_document(observation, event_id, now)
            self.repository.append(VERSION_EVENTS, event_id, base, token)
            self.repository.project(VERSIONS, event_id, base, token)
            compatibility_id = canonical_id("schema-compatibility", tenant, environment, event_id)
            compatibility = self._compatibility_document(observation, compatibility_id, now)
            self.repository.append(COMPATIBILITY_EVENTS, compatibility_id, compatibility, token)
            if observation.evaluation.change_set.changes:
                change_id = canonical_id("schema-change", tenant, environment, event_id)
                self.repository.append(
                    CHANGE_EVENTS, change_id, self._change_document(observation, change_id, now), token
                )
            subject = base | {
                "latest_version": observation.schema_version,
                "latest_compatibility": observation.evaluation.result.value,
                "event_id": event_id,
            }
            self.repository.project(SUBJECTS, observation.identity.subject_id, subject, token)
            self._bindings_and_impacts(observation, event_id, token, now)
            completed.append(event_id)
        # A replay after projection/impact failure repeats deterministic appends and converges.
        self.repository.checkpoint(tenant, environment, completed[-1] if completed else cursor, self.worker_id, token)
        return completed

    @staticmethod
    def _version_document(o: SchemaVersionObservation, event_id: str, ingested_at: datetime) -> dict[str, object]:
        return {
            "event_id": event_id,
            "tenant_id": o.identity.tenant_id,
            "environment": o.identity.environment,
            "integration_id": o.integration_id,
            "registry_id": o.identity.registry_id,
            "subject_id": o.identity.subject_id,
            "subject_fingerprint": canonical_id(
                "subject-fingerprint", o.identity.tenant_id, o.identity.environment, o.identity.subject
            ),
            "schema_version": o.schema_version,
            "schema_id": o.schema_id,
            "schema_type": o.schema_type,
            "schema_fingerprint": o.schema_fingerprint,
            "compatibility_mode": o.compatibility_mode,
            "reference_count": o.reference_count,
            "field_count": o.field_count,
            "structural_fingerprint": o.structural_fingerprint,
            "observed_at": o.observed_at.isoformat(),
            "ingested_at": ingested_at.isoformat(),
            "data_status": "measured",
            "source_coverage": 1.0,
            "confidence": o.evaluation.confidence,
            "measurement_method": "schema_registry_metadata",
            "schema_version_contract": "v1",
        }

    @staticmethod
    def _compatibility_document(o: SchemaVersionObservation, event_id: str, now: datetime) -> dict[str, object]:
        e = o.evaluation
        return {
            "event_id": event_id,
            "tenant_id": o.identity.tenant_id,
            "environment": o.identity.environment,
            "registry_id": o.identity.registry_id,
            "subject_id": o.identity.subject_id,
            "schema_version": o.schema_version,
            "evaluation_method": e.method,
            "authoritative": e.authoritative,
            "policy": e.policy.value,
            "result": e.result.value,
            "confidence": e.confidence,
            "limitations": list(e.limitations)[:20],
            "evaluated_at": now.isoformat(),
            "observed_at": o.observed_at.isoformat(),
            "evidence_refs": [],
        }

    @staticmethod
    def _change_document(o: SchemaVersionObservation, event_id: str, now: datetime) -> dict[str, object]:
        changes = o.evaluation.change_set
        return {
            "event_id": event_id,
            "tenant_id": o.identity.tenant_id,
            "environment": o.identity.environment,
            "registry_id": o.identity.registry_id,
            "subject_id": o.identity.subject_id,
            "schema_version": o.schema_version,
            "change_categories": list(changes.summary.change_categories),
            "change_counts": asdict(changes.summary),
            "field_hashes": [c.field.field_path_hash for c in changes.changes if c.field][:200],
            "technical_severity": changes.schema_change_severity.value,
            "observed_at": o.observed_at.isoformat(),
            "ingested_at": now.isoformat(),
        }

    def _bindings_and_impacts(
        self, o: SchemaVersionObservation, version_event_id: str, token: int, now: datetime
    ) -> None:
        if o.resource_binding and o.resource_binding.resource_id:
            binding_id = canonical_id(
                "schema-resource-binding",
                o.identity.tenant_id,
                o.identity.environment,
                o.identity.subject_id,
                o.resource_binding.resource_id,
            )
            document = {
                "event_id": binding_id,
                "tenant_id": o.identity.tenant_id,
                "environment": o.identity.environment,
                "subject_id": o.identity.subject_id,
                "resource_id": o.resource_binding.resource_id,
                "messaging_system": "kafka",
                "binding_method": o.resource_binding.binding_method,
                "binding_confidence": o.resource_binding.binding_confidence,
                "observed_at": o.observed_at.isoformat(),
                "evidence_refs": [version_event_id],
            }
            self.repository.project(BINDINGS, binding_id, document, token)
        for binding in o.application_bindings[:200]:
            application_binding_id = canonical_id(
                "schema-application-binding",
                o.identity.tenant_id,
                o.identity.environment,
                o.identity.subject_id,
                binding.application_id,
                binding.usage_role,
            )
            self.repository.project(
                BINDINGS,
                application_binding_id,
                {
                    "event_id": application_binding_id,
                    "tenant_id": o.identity.tenant_id,
                    "environment": o.identity.environment,
                    "subject_id": o.identity.subject_id,
                    "resource_id": binding.resource_id,
                    "application_id": binding.application_id,
                    "consumer_group_or_subscription": binding.consumer_group_or_subscription,
                    "schema_version": binding.schema_version,
                    "role": binding.usage_role,
                    "binding_method": binding.binding_method,
                    "binding_confidence": binding.confidence,
                    "known_supported_versions": list(binding.supported_schema_versions),
                    "observed_at": binding.observed_at.isoformat(),
                    "evidence_refs": list(binding.evidence_refs)[:50],
                },
                token,
            )
            if binding.usage_role != "consumer":
                continue
            exposure = evaluate_consumer_exposure(
                binding,
                o.evaluation,
                proven_incompatible=bool(
                    binding.supported_schema_versions and o.schema_version not in binding.supported_schema_versions
                ),
                runtime_schema_error_count=(o.runtime_schema_errors or {}).get(binding.application_id),
            )
            impact_id = canonical_id(
                "schema-impact",
                o.identity.tenant_id,
                o.identity.environment,
                version_event_id,
                binding.application_id,
                exposure.exposure_state.value,
            )
            document = {
                "event_id": impact_id,
                "tenant_id": o.identity.tenant_id,
                "environment": o.identity.environment,
                "subject_id": o.identity.subject_id,
                "consumer_id": binding.application_id,
                "consumer_group_or_subscription": binding.consumer_group_or_subscription,
                "resource_id": binding.resource_id,
                "exposure_state": exposure.exposure_state.value,
                "compatibility_state": exposure.compatibility_state.value,
                "binding_method": binding.binding_method,
                "binding_confidence": binding.confidence,
                "schema_error_count": exposure.observed_schema_errors,
                "confidence": binding.confidence * o.evaluation.confidence,
                "reason_codes": list(exposure.reason_codes),
                "evidence_refs": [version_event_id, *binding.evidence_refs][:50],
                "observed_at": now.isoformat(),
            }
            self.repository.append(IMPACT_EVENTS, impact_id, document, token)
            self.repository.project(
                IMPACTS,
                canonical_id(
                    "schema-impact-current",
                    o.identity.tenant_id,
                    o.identity.environment,
                    o.identity.subject_id,
                    binding.application_id,
                ),
                document,
                token,
            )
