"""Versioned lifecycle service for SLO definitions."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from packages.domain_model.slo import DataReliabilitySLODefinition

from .models import DefinitionRevision


class DataSLOService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _etag(value: DataReliabilitySLODefinition) -> str:
        body = value.model_dump_json(exclude={"etag", "updated_at"})
        return sha256(body.encode()).hexdigest()

    def create_definition(self, payload: dict, *, tenant_id: str, environment: str, actor: str, reason: str):
        if not reason.strip():
            raise ValueError("reason is required")
        now = datetime.now(timezone.utc)
        fields = {
            key: item
            for key, item in payload.items()
            if key
            not in {
                "id",
                "tenant_id",
                "environment",
                "state",
                "revision",
                "etag",
                "created_by",
                "created_at",
                "updated_at",
            }
        }
        value = DataReliabilitySLODefinition(
            **fields,
            id=payload.get("id", str(uuid4())),
            tenant_id=tenant_id,
            environment=environment,
            state="draft",
            revision=1,
            etag="pending",
            created_by=actor,
            created_at=now,
            updated_at=now,
        )
        value = value.model_copy(update={"etag": self._etag(value)})
        event = DefinitionRevision(value.id, 1, actor, reason, now, value.model_dump(mode="json"))
        self.repository.create_definition(value, event)
        return value

    def transition(self, tenant_id, environment, slo_id, state, *, actor, reason, expected_etag):
        if state not in {"active", "disabled", "archived"}:
            raise ValueError("invalid lifecycle transition")
        current = self.repository.get_definition(tenant_id, environment, slo_id)
        if current is None:
            raise KeyError(slo_id)
        if current.state == "archived":
            raise ValueError("archived definitions are immutable")
        now = datetime.now(timezone.utc)
        value = current.model_copy(
            update={"state": state, "revision": current.revision + 1, "updated_at": now, "etag": "pending"}
        )
        value = value.model_copy(update={"etag": self._etag(value)})
        revision = DefinitionRevision(slo_id, value.revision, actor, reason, now, value.model_dump(mode="json"))
        self.repository.update_definition(value, revision, expected_etag=expected_etag)
        return value
