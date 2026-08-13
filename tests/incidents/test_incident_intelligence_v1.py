from datetime import datetime, timedelta, timezone

import pytest

from services.incident_manager.intelligence.features import IncidentFeatures
from services.incident_manager.intelligence.fingerprint import incident_fingerprint
from services.incident_manager.intelligence.models import RelationshipStatus, SimilarityClassification
from services.incident_manager.intelligence.recurrence import family_identity, propose_recurrence, relationship_identity
from services.incident_manager.intelligence.repository import InMemoryIntelligenceRepository
from services.incident_manager.intelligence.similarity import FEATURE_POLICIES, score_similarity


def features(incident_id: str, **changes):
    values = dict(
        tenant_id="tenant-a",
        environment="prod",
        incident_id=incident_id,
        primary_asset="asset-1",
        affected_assets=("asset-1", "asset-2"),
        finding_types=("freshness_breach",),
        signal_types=("freshness_measurement",),
        rule_ids=("freshness-5m",),
        failure_categories=("stale",),
        data_product_ids=("orders",),
        business_services=("checkout",),
        recovery_characteristics=("verified",),
    )
    values.update(changes)
    return IncidentFeatures(**values)


def test_incident_fingerprint_is_deterministic_and_excludes_identity_revision():
    first = features("INC-1", source_revision="1:1")
    second = features("INC-2", source_revision="99:2")
    assert incident_fingerprint(first) == incident_fingerprint(second)
    assert incident_fingerprint(first) != incident_fingerprint(features("INC-2", failure_categories=("schema",)))


def test_identical_structured_features_score_high_with_explanation():
    result = score_similarity(features("INC-1"), features("INC-2"))
    assert result.classification == SimilarityClassification.VERY_HIGH
    assert result.similarity_score == 1
    assert result.confidence != result.similarity_score
    assert result.evidence_coverage > 0.7
    assert result.same_structural_signature
    assert result.matched_features


def test_missing_feature_is_unavailable_not_mismatch_or_perfect():
    result = score_similarity(
        features("INC-1", affected_assets=(), data_product_ids=()),
        features("INC-2", affected_assets=(), data_product_ids=()),
    )
    assert "affected_assets" in result.unavailable_features
    assert all(item.feature != "affected_assets" for item in result.matched_features + result.different_features)
    assert result.evidence_coverage < 1


def test_same_asset_alone_is_not_high_similarity():
    sparse_a = IncidentFeatures(tenant_id="tenant-a", environment="prod", incident_id="a", primary_asset="x")
    sparse_b = IncidentFeatures(tenant_id="tenant-a", environment="prod", incident_id="b", primary_asset="x")
    result = score_similarity(sparse_a, sparse_b)
    assert result.classification == SimilarityClassification.INSUFFICIENT_EVIDENCE
    assert result.confidence < 0.2


def test_scope_is_fail_closed():
    with pytest.raises(ValueError, match="cross-tenant"):
        score_similarity(features("a"), features("b", tenant_id="tenant-b"))
    with pytest.raises(ValueError, match="cross-environment"):
        score_similarity(features("a"), features("b", environment="dev"))


def test_feature_weight_normalization():
    assert sum(item.weight for item in FEATURE_POLICIES) == pytest.approx(1)


def test_high_similarity_creates_directional_candidate_not_confirmation():
    old, new = features("old"), features("new")
    now = datetime.now(timezone.utc)
    result = score_similarity(new, old, computed_at=now)
    recurrence = propose_recurrence(new, old, result, source_opened_at=now, candidate_opened_at=now - timedelta(days=1))
    assert recurrence is not None
    assert recurrence.prior_incident_id == "old" and recurrence.current_incident_id == "new"
    assert recurrence.status == RelationshipStatus.CANDIDATE


def test_recurrence_requires_order_and_excludes_merge_or_split():
    now = datetime.now(timezone.utc)
    result = score_similarity(features("a"), features("b"))
    assert (
        propose_recurrence(features("a"), features("b"), result, source_opened_at=None, candidate_opened_at=now) is None
    )
    assert (
        propose_recurrence(
            features("a", merged_from=("x",)),
            features("b"),
            result,
            source_opened_at=now,
            candidate_opened_at=now - timedelta(days=1),
        )
        is None
    )
    assert (
        propose_recurrence(
            features("a", split_from="x"),
            features("b"),
            result,
            source_opened_at=now,
            candidate_opened_at=now - timedelta(days=1),
        )
        is None
    )


def test_rejection_is_durable_and_occ_safe():
    now = datetime.now(timezone.utc)
    a, b = features("a"), features("b")
    proposal = propose_recurrence(
        a, b, score_similarity(a, b), source_opened_at=now, candidate_opened_at=now - timedelta(days=1)
    )
    repo = InMemoryIntelligenceRepository()
    repo.put_candidate(proposal)
    rejected = repo.decide(
        proposal.relationship_id,
        RelationshipStatus.REJECTED,
        actor="operator",
        reason="different event",
        expected_revision=1,
    )
    assert repo.put_candidate(proposal).status == RelationshipStatus.REJECTED
    with pytest.raises(Exception, match="revision conflict"):
        repo.decide(
            proposal.relationship_id, RelationshipStatus.CONFIRMED, actor="other", reason="no", expected_revision=1
        )
    assert rejected.actor == "operator"


def test_relationship_and_family_identity_are_deterministic_and_scope_bound():
    assert relationship_identity("t", "prod", "a", "b", "v1") == relationship_identity("t", "prod", "b", "a", "v1")
    assert relationship_identity("t", "prod", "a", "b", "v1") != relationship_identity("other", "prod", "a", "b", "v1")
    assert family_identity("t", "prod", features("a")) == family_identity("t", "prod", features("b"))
