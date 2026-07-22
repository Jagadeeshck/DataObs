"""Regression contract for the forward-only strict runtime mappings."""

from packages.domain_model.data_product import (
    DataProductDependencyProjection,
    DataProductImpactSummary,
    DataProductMembership,
    DataProductMembershipDecision,
    DataProductMembershipProposal,
)
from packages.elastic_store.manifest import (
    DATA_PRODUCT_DECISION_PROPERTIES,
    DATA_PRODUCT_DEPENDENCY_PROPERTIES,
    DATA_PRODUCT_IMPACT_PROPERTIES,
    DATA_PRODUCT_MEMBERSHIP_DEPENDENCY_RUNTIME_MIGRATION,
    DATA_PRODUCT_MEMBERSHIP_PROPERTIES,
    DATA_PRODUCT_PROPOSAL_PROPERTIES,
    migrations,
)


def test_0016_is_forward_only_resource_specific():
    migration = DATA_PRODUCT_MEMBERSHIP_DEPENDENCY_RUNTIME_MIGRATION
    assert migration in migrations()
    assert migration.migration_id == "0016_data_product_membership_dependency_runtime"
    assert migration.dependencies == ["0015_data_product_360_productization"]
    assert not migration.operations.get("mutable_indices")
    mappings = migration.operations["mapping_updates"]
    assert len(mappings) == 5
    assert len({id(value) for value in mappings.values()}) == 5


def test_complete_serializer_fields_are_admitted_by_strict_mappings():
    contracts = [
        (DataProductMembership, DATA_PRODUCT_MEMBERSHIP_PROPERTIES),
        (DataProductMembershipProposal, DATA_PRODUCT_PROPOSAL_PROPERTIES),
        (DataProductMembershipDecision, DATA_PRODUCT_DECISION_PROPERTIES),
        (DataProductDependencyProjection, DATA_PRODUCT_DEPENDENCY_PROPERTIES),
        (DataProductImpactSummary, DATA_PRODUCT_IMPACT_PROPERTIES),
    ]
    for model, properties in contracts:
        assert set(model.model_fields) <= set(properties), (
            model.__name__,
            sorted(set(model.model_fields) - set(properties)),
        )


def test_unknown_fields_remain_unmapped():
    for properties in [
        DATA_PRODUCT_MEMBERSHIP_PROPERTIES,
        DATA_PRODUCT_PROPOSAL_PROPERTIES,
        DATA_PRODUCT_DECISION_PROPERTIES,
        DATA_PRODUCT_DEPENDENCY_PROPERTIES,
        DATA_PRODUCT_IMPACT_PROPERTIES,
    ]:
        assert "unknown_field" not in properties
