"""Tenant-scoped persistence contract and deterministic test repository."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Protocol, Sequence

from packages.domain_model.slo import DataReliabilitySLODefinition, DataReliabilitySLOEvaluation

from .models import DefinitionRevision, RuntimeState


class DefinitionConflict(RuntimeError):
    pass


class FenceLost(RuntimeError):
    pass


class DataSLORepository(Protocol):
    def create_definition(self, value: DataReliabilitySLODefinition, revision: DefinitionRevision) -> None: ...
    def get_definition(self, tenant_id: str, environment: str, slo_id: str) -> DataReliabilitySLODefinition | None: ...
    def list_definitions(
        self, tenant_id: str, environment: str, *, limit: int, after: str | None = None
    ) -> Sequence[DataReliabilitySLODefinition]: ...
    def update_definition(
        self, value: DataReliabilitySLODefinition, revision: DefinitionRevision, *, expected_etag: str
    ) -> None: ...
    def list_revisions(
        self, tenant_id: str, environment: str, slo_id: str, *, limit: int
    ) -> Sequence[DefinitionRevision]: ...
    def append_evaluation(self, value: DataReliabilitySLOEvaluation) -> bool: ...
    def put_current(self, value: DataReliabilitySLOEvaluation, *, fencing_token: int) -> None: ...
    def list_due(
        self, tenant_id: str, environment: str, before: datetime, *, limit: int, after: str | None = None
    ) -> Sequence[RuntimeState]: ...
    def acquire_lease(
        self, tenant_id: str, environment: str, slo_id: str, worker_id: str, now: datetime, expires_at: datetime
    ) -> int | None: ...
    def get_runtime(self, tenant_id: str, environment: str, slo_id: str) -> RuntimeState: ...
    def checkpoint(self, state: RuntimeState, *, fencing_token: int) -> None: ...


class MemoryDataSLORepository:
    """Strictly scoped implementation intended for unit tests and local previews."""

    def __init__(self) -> None:
        self.definitions = {}
        self.revisions = {}
        self.evaluations = {}
        self.current = {}
        self.runtime = {}

    @staticmethod
    def _key(tenant_id: str, environment: str, slo_id: str):
        if not tenant_id or not environment:
            raise ValueError("tenant_id and environment are required")
        return tenant_id, environment, slo_id

    def create_definition(self, value, revision):
        key = self._key(value.tenant_id, value.environment, value.id)
        if key in self.definitions:
            raise DefinitionConflict("definition already exists")
        self.definitions[key] = deepcopy(value)
        self.revisions[key] = [revision]

    def get_definition(self, tenant_id, environment, slo_id):
        return deepcopy(self.definitions.get(self._key(tenant_id, environment, slo_id)))

    def list_definitions(self, tenant_id, environment, *, limit, after=None):
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        values = sorted(
            (v for (t, e, _), v in self.definitions.items() if (t, e) == (tenant_id, environment)), key=lambda v: v.id
        )
        if after is not None:
            values = [v for v in values if v.id > after]
        return deepcopy(values[:limit])

    def update_definition(self, value, revision, *, expected_etag):
        key = self._key(value.tenant_id, value.environment, value.id)
        current = self.definitions.get(key)
        if current is None:
            raise KeyError(value.id)
        if current.etag != expected_etag:
            raise DefinitionConflict("stale ETag")
        self.definitions[key] = deepcopy(value)
        self.revisions[key].append(revision)

    def list_revisions(self, tenant_id, environment, slo_id, *, limit):
        return deepcopy(self.revisions.get(self._key(tenant_id, environment, slo_id), [])[-limit:])

    def append_evaluation(self, value):
        key = self._key(value.tenant_id, value.environment, value.id)
        if key in self.evaluations:
            return False
        self.evaluations[key] = deepcopy(value)
        return True

    def put_current(self, value, *, fencing_token):
        state = self.runtime[self._key(value.tenant_id, value.environment, value.slo_id)]
        if state.fencing_token != fencing_token:
            raise FenceLost("worker no longer owns fence")
        self.current[self._key(value.tenant_id, value.environment, value.slo_id)] = deepcopy(value)

    def seed_runtime(self, state):
        self.runtime[self._key(state.tenant_id, state.environment, state.slo_id)] = state

    def list_due(self, tenant_id, environment, before, *, limit, after=None):
        values = [
            v
            for (t, e, _), v in self.runtime.items()
            if (t, e) == (tenant_id, environment) and v.next_evaluation_at <= before
        ]
        values.sort(key=lambda v: (v.next_evaluation_at, v.slo_id))
        if after:
            values = [v for v in values if v.slo_id > after]
        return values[: min(limit, 200)]

    def acquire_lease(self, tenant_id, environment, slo_id, worker_id, now, expires_at):
        from dataclasses import replace

        key = self._key(tenant_id, environment, slo_id)
        state = self.runtime[key]
        if state.lease_expires_at and state.lease_expires_at > now and state.lease_owner != worker_id:
            return None
        token = state.fencing_token + 1
        self.runtime[key] = replace(
            state,
            lease_owner=worker_id,
            lease_expires_at=expires_at,
            fencing_token=token,
            attempt_count=state.attempt_count + 1,
        )
        return token

    def get_runtime(self, tenant_id, environment, slo_id):
        return self.runtime[self._key(tenant_id, environment, slo_id)]

    def checkpoint(self, state, *, fencing_token):
        key = self._key(state.tenant_id, state.environment, state.slo_id)
        if self.runtime[key].fencing_token != fencing_token:
            raise FenceLost("worker no longer owns fence")
        self.runtime[key] = state
