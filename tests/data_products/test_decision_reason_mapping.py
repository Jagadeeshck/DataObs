from datetime import datetime, timezone

from packages.domain_model.data_product import DataProductMembershipDecision
from services.data_products.elasticsearch_repository import ElasticsearchDataProductRepository


def _decision() -> DataProductMembershipDecision:
    occurred_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return DataProductMembershipDecision(
        decision_id="decision-1",
        tenant_id="tenant-a",
        environment="prod",
        product_id="product-1",
        decision="accept",
        actor="operator",
        reason="contract approved",
        idempotency_key_hash="hash",
        request_fingerprint="fingerprint",
        decided_at=occurred_at,
        occurred_at=occurred_at,
    )


def test_decision_document_translates_domain_reason_to_mapped_field():
    document = ElasticsearchDataProductRepository._decision_document(_decision())
    assert document["decision_reason"] == "contract approved"
    assert "reason" not in document


def test_decision_mapping_round_trip_restores_domain_reason():
    document = ElasticsearchDataProductRepository._decision_document(_decision())
    restored = ElasticsearchDataProductRepository._decision_from_source(document)
    assert DataProductMembershipDecision.model_validate(restored).reason == "contract approved"
    assert "decision_reason" not in restored


def test_legacy_reason_document_remains_readable():
    legacy = _decision().model_dump(mode="json")
    restored = ElasticsearchDataProductRepository._decision_from_source(legacy)
    assert DataProductMembershipDecision.model_validate(restored).reason == "contract approved"
