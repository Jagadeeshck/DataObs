"""Durable, tenant-scoped persistence boundary for job/run reliability.

The memory implementation deliberately has the same public surface as the
Elasticsearch adapter.  Runtime and HTTP code therefore never needs to know
about a store's internal collections.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Protocol

from packages.domain_model.job_run import (
    ExpectedRun,
    JobReliabilitySnapshot,
    ReliabilityPolicy,
    RunReliabilityEvaluation,
)


class ConflictError(RuntimeError):
    """An OCC precondition or fenced ownership check failed."""


class ReliabilityRepository(Protocol):
    def get_policy(self, tenant_id: str, environment: str, job_id: str) -> ReliabilityPolicy | None: ...
    def put_policy(self, policy: ReliabilityPolicy, if_match: str | None) -> ReliabilityPolicy: ...
    def list_policy_history(self, tenant_id: str, environment: str, job_id: str) -> list[ReliabilityPolicy]: ...
    def create_expected_run(self, expected: ExpectedRun) -> bool: ...
    def list_expected_runs(self, tenant_id: str, environment: str, job_id: str) -> list[ExpectedRun]: ...
    def associate_expected_run(self, expected_run_id: str, run_id: str, *, reason: str) -> ExpectedRun: ...
    def append_evaluation(self, evaluation: RunReliabilityEvaluation) -> bool: ...
    def append_snapshot(self, snapshot: JobReliabilitySnapshot) -> bool: ...
    def current_snapshot(self, tenant_id: str, environment: str, job_id: str) -> JobReliabilitySnapshot | None: ...
    def claim_lease(self, partition: str, owner: str, now: datetime, ttl_seconds: int) -> int: ...
    def release_lease(self, partition: str, owner: str, token: int) -> None: ...
    def read_checkpoint(self, partition: str) -> datetime | None: ...
    def update_checkpoint(self, partition: str, owner: str, fencing_token: int, value: datetime) -> None: ...


class MemoryReliabilityRepository:
    """Deterministic repository used by tests and explicitly configured demos."""

    def __init__(self):
        self._policies: dict[tuple[str, str, str], ReliabilityPolicy] = {}
        self._policy_history: dict[tuple[str, str, str], list[ReliabilityPolicy]] = {}
        self._expected: dict[str, ExpectedRun] = {}
        self._evaluations: dict[str, RunReliabilityEvaluation] = {}
        self._snapshots: list[JobReliabilitySnapshot] = []
        self._current: dict[tuple[str, str, str], JobReliabilitySnapshot] = {}
        self._leases: dict[str, dict[str, Any]] = {}
        self._checkpoints: dict[str, datetime] = {}
        self._actions: dict[tuple[str, str, str], dict[str, Any]] = {}

    def get_policy(self, tenant_id: str, environment: str, job_id: str) -> ReliabilityPolicy | None:
        value = self._policies.get((tenant_id, environment, job_id))
        return deepcopy(value) if value else None

    def put_policy(self, policy: ReliabilityPolicy, if_match: str | None) -> ReliabilityPolicy:
        key = (policy.tenant_id, policy.environment, policy.job_id)
        current = self._policies.get(key)
        if current is not None and if_match != current.etag:
            raise ConflictError("reliability policy ETag conflict")
        if current is None and if_match not in (None, "*"):
            raise ConflictError("reliability policy does not exist")
        if current is not None and policy.revision != current.revision + 1:
            raise ConflictError("reliability policy revision must increment exactly once")
        self._policies[key] = deepcopy(policy)
        self._policy_history.setdefault(key, []).append(deepcopy(policy))
        return deepcopy(policy)

    def list_policy_history(self, tenant_id: str, environment: str, job_id: str) -> list[ReliabilityPolicy]:
        return deepcopy(self._policy_history.get((tenant_id, environment, job_id), []))

    def create_expected_run(self, expected: ExpectedRun) -> bool:
        if expected.expected_run_id in self._expected:
            return False
        self._expected[expected.expected_run_id] = deepcopy(expected)
        return True

    append_expected_run = create_expected_run

    def get_expected_run(self, tenant_id: str, environment: str, expected_run_id: str) -> ExpectedRun | None:
        value = self._expected.get(expected_run_id)
        if not value or (value.tenant_id, value.environment) != (tenant_id, environment):
            return None
        return deepcopy(value)

    def list_expected_runs(self, tenant_id: str, environment: str, job_id: str) -> list[ExpectedRun]:
        return deepcopy(
            sorted(
                (
                    x
                    for x in self._expected.values()
                    if (x.tenant_id, x.environment, x.job_id) == (tenant_id, environment, job_id)
                ),
                key=lambda x: (x.scheduled_at, x.expected_run_id),
            )
        )

    def list_unassociated_expected_runs(self, tenant_id: str, environment: str, job_id: str) -> list[ExpectedRun]:
        return [x for x in self.list_expected_runs(tenant_id, environment, job_id) if x.actual_run_id is None]

    def associate_expected_run(self, expected_run_id: str, run_id: str, *, reason: str) -> ExpectedRun:
        current = self._expected.get(expected_run_id)
        if current is None:
            raise KeyError(expected_run_id)
        if current.actual_run_id not in (None, run_id):
            raise ConflictError("expected run is already associated")
        for value in self._expected.values():
            if value.actual_run_id == run_id and value.expected_run_id != expected_run_id:
                raise ConflictError("actual run is already associated")
        update = current.model_copy(deep=True) if hasattr(current, "model_copy") else current.copy(deep=True)
        update.actual_run_id = run_id
        update.reason_codes = sorted(set(update.reason_codes + [reason]))
        self._expected[expected_run_id] = update
        return deepcopy(update)

    def append_evaluation(self, evaluation: RunReliabilityEvaluation) -> bool:
        if evaluation.evaluation_id in self._evaluations:
            return False
        self._evaluations[evaluation.evaluation_id] = deepcopy(evaluation)
        return True

    def list_evaluations(
        self, tenant_id: str, environment: str, job_id: str | None = None
    ) -> list[RunReliabilityEvaluation]:
        values = [x for x in self._evaluations.values() if (x.tenant_id, x.environment) == (tenant_id, environment)]
        if job_id is not None:
            values = [x for x in values if x.job_id == job_id]
        return deepcopy(sorted(values, key=lambda x: (x.evaluated_at, x.evaluation_id)))

    def append_snapshot(self, snapshot: JobReliabilitySnapshot) -> bool:
        identity = (snapshot.tenant_id, snapshot.environment, snapshot.job_id, snapshot.observed_at)
        if any((x.tenant_id, x.environment, x.job_id, x.observed_at) == identity for x in self._snapshots):
            return False
        self._snapshots.append(deepcopy(snapshot))
        self._current[identity[:3]] = deepcopy(snapshot)
        return True

    def current_snapshot(self, tenant_id: str, environment: str, job_id: str) -> JobReliabilitySnapshot | None:
        value = self._current.get((tenant_id, environment, job_id))
        return deepcopy(value) if value else None

    def list_reliability_history(self, tenant_id: str, environment: str, job_id: str) -> list[JobReliabilitySnapshot]:
        return deepcopy(
            sorted(
                (
                    x
                    for x in self._snapshots
                    if (x.tenant_id, x.environment, x.job_id) == (tenant_id, environment, job_id)
                ),
                key=lambda x: x.observed_at,
            )
        )

    def claim_lease(self, partition: str, owner: str, now: datetime, ttl_seconds: int) -> int:
        from datetime import timedelta

        lease = self._leases.get(partition)
        if lease and lease["expires_at"] > now and lease["owner"] != owner:
            raise ConflictError("partition already leased")
        token = int(lease["token"]) + 1 if lease else 1
        self._leases[partition] = {"owner": owner, "token": token, "expires_at": now + timedelta(seconds=ttl_seconds)}
        return token

    def renew_lease(self, partition: str, owner: str, token: int, now: datetime, ttl_seconds: int) -> None:
        from datetime import timedelta

        self._require_owner(partition, owner, token)
        self._leases[partition]["expires_at"] = now + timedelta(seconds=ttl_seconds)

    def release_lease(self, partition: str, owner: str, token: int) -> None:
        self._require_owner(partition, owner, token)
        del self._leases[partition]

    def _require_owner(self, partition: str, owner: str, token: int) -> None:
        lease = self._leases.get(partition)
        if not lease or (lease["owner"], lease["token"]) != (owner, token):
            raise ConflictError("stale lease owner")

    def read_checkpoint(self, partition: str) -> datetime | None:
        return self._checkpoints.get(partition)

    def update_checkpoint(self, partition: str, owner: str, fencing_token: int, value: datetime) -> None:
        self._require_owner(partition, owner, fencing_token)
        current = self._checkpoints.get(partition)
        if current and value < current:
            raise ConflictError("checkpoint cannot move backwards")
        self._checkpoints[partition] = value

    def runtime_health(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        return {
            "active_leases": sum(x["expires_at"] > now for x in self._leases.values()),
            "expired_leases": sum(x["expires_at"] <= now for x in self._leases.values()),
            "partitions": len(self._checkpoints),
        }

    def reserve_action(
        self, tenant_id: str, environment: str, idempotency_key: str, request: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        key = (tenant_id, environment, idempotency_key)
        current = self._actions.get(key)
        if current:
            if current["fingerprint"] != request["fingerprint"]:
                raise ConflictError("idempotency key was used for a different request")
            return deepcopy(current), True
        self._actions[key] = deepcopy(request)
        return deepcopy(request), False


class ElasticsearchReliabilityRepository:
    """Elasticsearch adapter using only fixed aliases and guarded writes."""

    POLICY = "dataobs-job-reliability-policy-v1-write"
    EXPECTED = "dataobs-expected-run-current-v1-write"
    CURRENT = "dataobs-job-reliability-current-v1-write"
    RUNTIME = "dataobs-job-reliability-runtime-state-v1-write"
    EVALUATIONS = "metrics-dataobs.job-reliability-default"
    EVENTS = "logs-dataobs.job-reliability-event-default"

    def __init__(self, client):
        self.client = client

    @staticmethod
    def _id(*parts: str) -> str:
        return hashlib.sha256("\0".join(parts).encode()).hexdigest()

    @staticmethod
    def _dump(value: Any) -> dict[str, Any]:
        return value.model_dump(mode="json") if hasattr(value, "model_dump") else value.dict()

    def get_policy(self, tenant_id: str, environment: str, job_id: str) -> ReliabilityPolicy | None:
        try:
            hit = self.client.get(index=self.POLICY, id=self._id(tenant_id, environment, job_id))
        except Exception as exc:
            if getattr(exc, "status_code", None) == 404:
                return None
            raise
        source = hit["_source"]
        if (source.get("tenant_id"), source.get("environment")) != (tenant_id, environment):
            return None
        return ReliabilityPolicy(**source)

    def put_policy(self, policy: ReliabilityPolicy, if_match: str | None) -> ReliabilityPolicy:
        identity = self._id(policy.tenant_id, policy.environment, policy.job_id)
        try:
            hit = self.client.get(index=self.POLICY, id=identity)
        except Exception as exc:
            if getattr(exc, "status_code", None) != 404:
                raise
            hit = None
        if hit:
            current = ReliabilityPolicy(**hit["_source"])
            if current.etag != if_match or policy.revision != current.revision + 1:
                raise ConflictError("reliability policy ETag conflict")
            self.client.index(
                index=self.POLICY,
                id=identity,
                document=self._dump(policy),
                if_seq_no=hit["_seq_no"],
                if_primary_term=hit["_primary_term"],
            )
        else:
            if if_match not in (None, "*"):
                raise ConflictError("reliability policy does not exist")
            self.client.create(index=self.POLICY, id=identity, document=self._dump(policy))
        self.client.create(
            index=self.EVENTS,
            id=self._id(identity, str(policy.revision)),
            document={**self._dump(policy), "event_type": "policy_revision"},
        )
        return policy

    def create_expected_run(self, expected: ExpectedRun) -> bool:
        try:
            self.client.create(index=self.EXPECTED, id=expected.expected_run_id, document=self._dump(expected))
            return True
        except Exception as exc:
            if getattr(exc, "status_code", None) == 409:
                return False
            raise

    append_expected_run = create_expected_run

    def append_evaluation(self, evaluation: RunReliabilityEvaluation) -> bool:
        try:
            self.client.create(index=self.EVALUATIONS, id=evaluation.evaluation_id, document=self._dump(evaluation))
            return True
        except Exception as exc:
            if getattr(exc, "status_code", None) == 409:
                return False
            raise

    def append_snapshot(self, snapshot: JobReliabilitySnapshot) -> bool:
        evidence_id = self._id(
            snapshot.tenant_id, snapshot.environment, snapshot.job_id, snapshot.observed_at.isoformat()
        )
        try:
            self.client.create(
                index=self.EVALUATIONS, id=evidence_id, document={**self._dump(snapshot), "document_type": "snapshot"}
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) == 409:
                return False
            raise
        self.client.index(
            index=self.CURRENT,
            id=self._id(snapshot.tenant_id, snapshot.environment, snapshot.job_id),
            document=self._dump(snapshot),
        )
        return True
