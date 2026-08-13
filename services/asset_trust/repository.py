"""Tenant-safe persistence contract and deterministic memory implementation."""

from copy import deepcopy
from typing import Protocol

from packages.domain_model.asset_trust import AssetTrustPolicy, AssetTrustScore


class PolicyConflict(RuntimeError):
    pass


class AssetTrustRepository(Protocol):
    def create_policy(self, tenant_id: str, environment: str, policy: AssetTrustPolicy) -> None: ...
    def get_policy(self, tenant_id: str, environment: str, policy_id: str) -> AssetTrustPolicy | None: ...
    def list_policies(self, tenant_id: str, environment: str, *, limit: int, after: str | None = None): ...
    def update_policy(
        self, tenant_id: str, environment: str, policy: AssetTrustPolicy, *, expected_etag: str
    ) -> None: ...
    def append_score(self, score: AssetTrustScore) -> bool: ...
    def get_current_score(self, tenant_id: str, environment: str, asset_id: str) -> AssetTrustScore | None: ...
    def list_score_history(self, tenant_id: str, environment: str, asset_id: str, *, limit: int, after=None): ...
    def list_assets_by_score(self, tenant_id: str, environment: str, *, limit: int, maximum_score=None): ...
    def bulk_get_scores(self, tenant_id: str, environment: str, asset_ids: list[str]): ...
    def runtime_health(self, tenant_id: str, environment: str) -> dict: ...


class MemoryAssetTrustRepository:
    def __init__(self):
        self.policies, self.scores, self.current = {}, {}, {}

    @staticmethod
    def _scope(tenant_id, environment):
        if not tenant_id or not environment:
            raise ValueError("tenant_id and environment are required")
        return tenant_id, environment

    def create_policy(self, tenant_id, environment, policy):
        key = self._scope(tenant_id, environment) + (policy.policy_id,)
        if key in self.policies:
            raise PolicyConflict("policy already exists")
        self.policies[key] = deepcopy(policy)

    def get_policy(self, tenant_id, environment, policy_id):
        return deepcopy(self.policies.get(self._scope(tenant_id, environment) + (policy_id,)))

    def list_policies(self, tenant_id, environment, *, limit, after=None):
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        values = [v for (t, e, _), v in self.policies.items() if (t, e) == self._scope(tenant_id, environment)]
        return deepcopy(
            [v for v in sorted(values, key=lambda x: x.policy_id) if after is None or v.policy_id > after][:limit]
        )

    def update_policy(self, tenant_id, environment, policy, *, expected_etag):
        key = self._scope(tenant_id, environment) + (policy.policy_id,)
        current = self.policies.get(key)
        if current is None:
            raise KeyError(policy.policy_id)
        if current.etag != expected_etag:
            raise PolicyConflict("stale ETag")
        if policy.revision != current.revision + 1:
            raise PolicyConflict("revision must increment exactly once")
        self.policies[key] = deepcopy(policy)

    def append_score(self, score):
        scope = self._scope(score.tenant_id, score.environment)
        key = scope + (score.score_id,)
        if key in self.scores:
            return False
        self.scores[key] = deepcopy(score)
        current_key = scope + (score.asset_id,)
        current = self.current.get(current_key)
        if current is None or score.calculated_at >= current.calculated_at:
            self.current[current_key] = deepcopy(score)
        return True

    def get_current_score(self, tenant_id, environment, asset_id):
        return deepcopy(self.current.get(self._scope(tenant_id, environment) + (asset_id,)))

    def list_score_history(self, tenant_id, environment, asset_id, *, limit, after=None):
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        scope = self._scope(tenant_id, environment)
        values = [v for (t, e, _), v in self.scores.items() if (t, e) == scope and v.asset_id == asset_id]
        values.sort(key=lambda v: (v.calculated_at, v.score_id), reverse=True)
        if after:
            values = [v for v in values if v.score_id < after]
        return deepcopy(values[:limit])

    def list_assets_by_score(self, tenant_id, environment, *, limit, maximum_score=None):
        scope = self._scope(tenant_id, environment)
        values = [v for (t, e, _), v in self.current.items() if (t, e) == scope and v.score is not None]
        if maximum_score is not None:
            values = [v for v in values if v.score <= maximum_score]
        return deepcopy(sorted(values, key=lambda v: (v.score, v.asset_id))[: min(limit, 200)])

    def bulk_get_scores(self, tenant_id, environment, asset_ids):
        if len(asset_ids) > 500:
            raise ValueError("bulk request exceeds 500 assets")
        return {asset: self.get_current_score(tenant_id, environment, asset) for asset in asset_ids}

    def runtime_health(self, tenant_id, environment):
        scope = self._scope(tenant_id, environment)
        return {"status": "healthy", "current_scores": sum((t, e) == scope for t, e, _ in self.current)}
