import pytest

from packages.domain_model.data_product import DataProduct, DataProductCriticality, DataProductOwner
from services.data_products.idempotency import IdempotencyConflict
from services.data_products.membership_service import DataProductMembershipService
from services.data_products.memory_repository import MemoryDataProductRepository
from services.data_products.repository import ProductVersionConflict


def service():
    repository = MemoryDataProductRepository()
    repository.create_product(
        DataProduct(
            id="orders",
            tenant_id="tenant-a",
            environment="prod",
            etag="v1",
            name="Orders",
            domain="commerce",
            criticality=DataProductCriticality.HIGH,
            owner=DataProductOwner(team="data"),
        )
    )
    return repository, DataProductMembershipService(repository)


def test_proposal_revision_source_accept_replay_and_exclusion_replay():
    repository, application = service()
    first = application.generate_lineage_proposals(
        "tenant-a", "prod", "orders", evidence=[("table", "asset", "lineage:b"), ("table", "asset", "lineage:a")]
    )
    assert (first.generated, first.existing) == (1, 0)
    assert (
        application.generate_lineage_proposals(
            "tenant-a",
            "prod",
            "orders",
            evidence=[
                ("table", "asset", "lineage:a"),
                ("table", "asset", "lineage:b"),
                ("table", "asset", "lineage:a"),
            ],
        ).existing
        == 1
    )
    proposal = application.list_proposals("tenant-a", "prod", "orders").items[0]
    assert proposal.source == "lineage"
    changed = application.generate_lineage_proposals(
        "tenant-a", "prod", "orders", evidence=[("table", "asset", "lineage:c")]
    )
    assert (changed.generated, changed.superseded) == (1, 1)
    proposal = repository.get_membership_proposal("tenant-a", "prod", "orders", proposal.proposal_id)
    assert proposal and proposal.proposal_revision == 2

    accepted = application.accept_proposal(
        "tenant-a",
        "prod",
        "orders",
        proposal.proposal_id,
        actor="reviewer",
        reason="verified",
        idempotency_key="accept-key",
        expected_revision=2,
    )
    assert accepted.membership and accepted.membership.source == "proposal"
    assert accepted.proposal.state == "accepted"
    replay = application.accept_proposal(
        "tenant-a",
        "prod",
        "orders",
        proposal.proposal_id,
        actor="reviewer",
        reason="verified",
        idempotency_key="accept-key",
        expected_revision=2,
    )
    assert replay.replayed and replay.operation_id == accepted.operation_id

    excluded = application.exclude_member(
        "tenant-a",
        "prod",
        "orders",
        accepted.membership.membership_id,
        actor="reviewer",
        reason="out of scope",
        idempotency_key="exclude-key",
        expected_etag=accepted.membership.etag,
    )
    replayed = application.exclude_member(
        "tenant-a",
        "prod",
        "orders",
        accepted.membership.membership_id,
        actor="reviewer",
        reason="out of scope",
        idempotency_key="exclude-key",
        expected_etag=accepted.membership.etag,
    )
    assert excluded.membership.state == "excluded" and replayed.replayed
    assert len(repository.decisions) == 4


def test_dependency_source_and_decision_conflicts():
    repository, application = service()
    application.generate_dependency_proposals(
        "tenant-a", "prod", "orders", evidence=[("upstream", "asset", "dependency:1")]
    )
    proposal = application.list_proposals("tenant-a", "prod", "orders").items[0]
    assert proposal.source == "dependency"
    with pytest.raises(ProductVersionConflict, match="proposal_revision_conflict"):
        application.reject_proposal(
            "tenant-a",
            "prod",
            "orders",
            proposal.proposal_id,
            actor="reviewer",
            reason="no",
            idempotency_key="reject-key",
            expected_revision=2,
        )
    with pytest.raises(IdempotencyConflict):
        application.reject_proposal(
            "tenant-a",
            "prod",
            "orders",
            proposal.proposal_id,
            actor="reviewer",
            reason="different",
            idempotency_key="reject-key",
            expected_revision=1,
        )
