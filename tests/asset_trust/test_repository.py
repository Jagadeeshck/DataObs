from dataclasses import replace
from datetime import datetime, timezone

import pytest

from packages.domain_model.asset_trust import AssetTrustPolicy
from services.asset_trust.repository import MemoryAssetTrustRepository, PolicyConflict
from tests.asset_trust.test_scoring import calculate, ev


def test_policy_occ_and_tenant_isolation():
    repo = MemoryAssetTrustRepository()
    policy = AssetTrustPolicy(policy_id="p", name="P", etag="one")
    repo.create_policy("a", "prod", policy)
    assert repo.get_policy("b", "prod", "p") is None
    with pytest.raises(PolicyConflict):
        repo.update_policy("a", "prod", policy.model_copy(update={"revision": 2}), expected_etag="stale")
    repo.update_policy("a", "prod", policy.model_copy(update={"revision": 2, "etag": "two"}), expected_etag="one")


def test_append_is_idempotent_history_is_immutable_and_scoped():
    repo = MemoryAssetTrustRepository()
    score = calculate([ev("quality"), ev("freshness")])
    assert repo.append_score(score) is True
    assert repo.append_score(score) is False
    assert len(repo.list_score_history("t", "prod", "a", limit=10)) == 1
    assert repo.get_current_score("other", "prod", "a") is None
