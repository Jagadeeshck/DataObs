"""Tenant-scoped persistence boundary for the reliability runtime."""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol

from packages.domain_model.job_run import ExpectedRun, JobReliabilitySnapshot, ReliabilityPolicy


class ConflictError(RuntimeError):
    pass


class ReliabilityRepository(Protocol):
    def get_policy(self, tenant_id: str, environment: str, job_id: str) -> ReliabilityPolicy | None: ...
    def put_policy(self, policy: ReliabilityPolicy, if_match: str | None) -> ReliabilityPolicy: ...
    def append_expected_run(self, expected: ExpectedRun) -> None: ...
    def append_snapshot(self, snapshot: JobReliabilitySnapshot) -> None: ...


class MemoryReliabilityRepository:
    """Deterministic test/demo repository; production wiring must use Elasticsearch."""

    def __init__(self):
        self._policies: dict[tuple[str, str, str], ReliabilityPolicy] = {}
        self.expected_runs: dict[str, ExpectedRun] = {}
        self.snapshots: list[JobReliabilitySnapshot] = []

    def get_policy(self, tenant_id: str, environment: str, job_id: str) -> ReliabilityPolicy | None:
        value = self._policies.get((tenant_id, environment, job_id))
        return deepcopy(value) if value else None

    def put_policy(self, policy: ReliabilityPolicy, if_match: str | None) -> ReliabilityPolicy:
        key = (policy.tenant_id, policy.environment, policy.job_id)
        current = self._policies.get(key)
        if current and if_match != current.etag:
            raise ConflictError("reliability policy ETag conflict")
        if not current and if_match not in (None, "*"):
            raise ConflictError("reliability policy does not exist")
        self._policies[key] = deepcopy(policy)
        return deepcopy(policy)

    def append_expected_run(self, expected: ExpectedRun) -> None:
        # Deterministic IDs make replay idempotent while later corrections remain separate events upstream.
        self.expected_runs.setdefault(expected.expected_run_id, deepcopy(expected))

    def append_snapshot(self, snapshot: JobReliabilitySnapshot) -> None:
        self.snapshots.append(deepcopy(snapshot))


class ElasticsearchReliabilityRepository:
    """Production adapter using scoped document IDs and optimistic concurrency."""

    POLICY_INDEX = "dataobs-job-reliability-policy-v1-write"

    def __init__(self, client):
        self.client = client

    @staticmethod
    def _id(tenant_id: str, environment: str, job_id: str) -> str:
        import hashlib

        return hashlib.sha256(f"{tenant_id}\0{environment}\0{job_id}".encode()).hexdigest()

    def get_policy(self, tenant_id: str, environment: str, job_id: str) -> ReliabilityPolicy | None:
        try:
            hit = self.client.get(index=self.POLICY_INDEX, id=self._id(tenant_id, environment, job_id))
        except Exception as exc:
            if getattr(exc, "status_code", None) == 404:
                return None
            raise
        source = hit["_source"]
        if source.get("tenant_id") != tenant_id or source.get("environment") != environment:
            return None
        return ReliabilityPolicy(**source)

    def put_policy(self, policy: ReliabilityPolicy, if_match: str | None) -> ReliabilityPolicy:
        current = self.get_policy(policy.tenant_id, policy.environment, policy.job_id)
        if current and current.etag != if_match:
            raise ConflictError("reliability policy ETag conflict")
        self.client.index(
            index=self.POLICY_INDEX,
            id=self._id(policy.tenant_id, policy.environment, policy.job_id),
            document=policy.model_dump(mode="json") if hasattr(policy, "model_dump") else policy.dict(),
        )
        return policy
