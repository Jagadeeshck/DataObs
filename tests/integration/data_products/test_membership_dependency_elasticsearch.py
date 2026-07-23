"""Focused real-Elasticsearch contract (enabled by the integration harness)."""

import os
from datetime import timedelta

import pytest
from elasticsearch import Elasticsearch

from packages.domain_model.base import utc_now
from packages.domain_model.data_product import DataProductDependencyProjection
from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository
from services.data_products.operation_state import (
    DataProductOperationPlan,
    DataProductOperationState,
    OperationClaimConflict,
)
from services.data_products.reconciliation import _checksum
from services.data_products.repository import DependencyEdgeSuperseded


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="real Elasticsearch opt-in")
def test_real_elasticsearch_membership_dependency_profile_is_selected():
    client = Elasticsearch(os.environ["ELASTICSEARCH_URL"])
    repository = ElasticsearchDataProductRepository(client)
    assert client.info()["version"]["number"].startswith("9.4.2")
    readiness = repository.readiness()
    assert readiness["ready"], readiness


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="real Elasticsearch opt-in")
def test_real_elasticsearch_operation_claim_is_occ_fenced():
    repository = ElasticsearchDataProductRepository(Elasticsearch(os.environ["ELASTICSEARCH_URL"]))
    now = utc_now()
    operation_id = f"integration-claim-{now.timestamp()}"
    payload = {"request_fingerprint": "integration-fingerprint"}
    plan = DataProductOperationPlan(
        f"plan:{operation_id}",
        "integration-tenant",
        "certification",
        "product",
        operation_id,
        "manual_membership",
        _checksum(payload),
        payload,
    )
    repository.save_operation_plan(plan)
    repository.create_operation_state(
        DataProductOperationState(
            operation_id,
            "integration-tenant",
            "certification",
            "product",
            "manual_membership",
            "pending",
            0,
            now,
            plan_reference=plan.reference,
        )
    )
    state = repository.get_operation_state("integration-tenant", "certification", operation_id)
    assert state is not None
    claim = repository.claim_operation(
        "integration-tenant",
        "certification",
        operation_id,
        worker_id="worker-one",
        now=now,
        expires_at=now + timedelta(seconds=30),
        expected_seq_no=state.seq_no,
        expected_primary_term=state.primary_term,
    )
    assert claim.generation == 1
    with pytest.raises(OperationClaimConflict):
        repository.claim_operation(
            "integration-tenant",
            "certification",
            operation_id,
            worker_id="worker-two",
            now=now,
            expires_at=now + timedelta(seconds=30),
            expected_seq_no=state.seq_no,
            expected_primary_term=state.primary_term,
        )


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="real Elasticsearch opt-in")
def test_real_elasticsearch_newer_dependency_edge_fences_stale_worker():
    repository = ElasticsearchDataProductRepository(Elasticsearch(os.environ["ELASTICSEARCH_URL"]))
    unique = str(utc_now().timestamp())

    def edge(revision):
        return DataProductDependencyProjection(
            tenant_id="integration-tenant",
            environment="certification",
            product_id=f"edge-product-{unique}",
            upstream_product_id="upstream",
            product_revision=revision,
            graph_version=f"graph-{revision}",
            removed=False,
        )

    repository.apply_dependency_upsert_chunk(
        "integration-tenant", "certification", f"edge-product-{unique}", (edge(2),)
    )
    with pytest.raises(DependencyEdgeSuperseded):
        repository.apply_dependency_upsert_chunk(
            "integration-tenant", "certification", f"edge-product-{unique}", (edge(1),)
        )
    snapshot = repository.read_complete_dependency_snapshot(
        "integration-tenant", "certification", f"edge-product-{unique}", maximum=10
    )
    assert snapshot.dependencies[0].product_revision == 2
