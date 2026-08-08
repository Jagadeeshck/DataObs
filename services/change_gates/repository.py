from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Protocol


def evaluation_id(
    tenant: str,
    environment: str,
    repository: str,
    project: str,
    pr: str,
    base_sha: str,
    head_sha: str,
    policy_fingerprint: str,
) -> str:
    value = "\x00".join((tenant, environment, repository, project, pr, base_sha, head_sha, policy_fingerprint))
    return "cge_" + sha256(value.encode()).hexdigest()[:32]


class ChangeGateRepository(Protocol):
    def start_evaluation(self, tenant_id: str, environment: str, evaluation: dict) -> dict: ...
    def append_check_result(self, tenant_id: str, environment: str, evaluation_id: str, check: dict) -> None: ...
    def complete_evaluation(self, tenant_id: str, environment: str, evaluation_id: str, result: dict) -> dict: ...
    def get_evaluation(self, tenant_id: str, environment: str, evaluation_id: str) -> dict | None: ...


class MemoryChangeGateRepository:
    """Bounded test repository. Production wiring must use ElasticsearchChangeGateRepository."""

    def __init__(self) -> None:
        self._evaluations: dict[tuple[str, str, str], dict] = {}
        self._checks: dict[tuple[str, str, str], list[dict]] = {}

    def start_evaluation(self, tenant_id, environment, evaluation):
        key = (tenant_id, environment, evaluation["evaluation_id"])
        self._evaluations.setdefault(key, deepcopy(evaluation))
        return deepcopy(self._evaluations[key])

    def append_check_result(self, tenant_id, environment, evaluation_id, check):
        key = (tenant_id, environment, evaluation_id)
        if key not in self._evaluations:
            raise KeyError(evaluation_id)
        bucket = self._checks.setdefault(key, [])
        if not any(x["check_id"] == check["check_id"] for x in bucket):
            bucket.append(deepcopy(check))

    def complete_evaluation(self, tenant_id, environment, evaluation_id, result):
        key = (tenant_id, environment, evaluation_id)
        if key not in self._evaluations:
            raise KeyError(evaluation_id)
        self._evaluations[key].update(deepcopy(result))
        self._evaluations[key]["checks"] = deepcopy(self._checks.get(key, []))
        return deepcopy(self._evaluations[key])

    def get_evaluation(self, tenant_id, environment, evaluation_id):
        value = self._evaluations.get((tenant_id, environment, evaluation_id))
        return deepcopy(value) if value else None

    def list_evaluations(self, tenant_id, environment, limit=100):
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return [deepcopy(v) for (t, e, _), v in self._evaluations.items() if (t, e) == (tenant_id, environment)][:limit]
