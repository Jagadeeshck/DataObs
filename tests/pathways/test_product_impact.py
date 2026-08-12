import pytest

from packages.pathways.product_impact import (
    ExposureState,
    evaluate_exposure,
    exposure_confidence,
    exposure_score,
    impact_identity,
)
from services.product_query.stream_product_impact import StreamProductImpactResolver


@pytest.mark.parametrize(
    ("stream", "product", "slo", "expected"),
    [
        (False, False, False, ExposureState.LINKED),
        (True, False, False, ExposureState.POTENTIALLY_EXPOSED),
        (True, True, False, ExposureState.OBSERVED_DEGRADATION),
        (True, False, True, ExposureState.SLO_IMPACT_OBSERVED),
    ],
)
def test_dependency_is_not_impact(stream, product, slo, expected):
    assert evaluate_exposure(stream_degraded=stream, product_degraded=product, related_slo_failed=slo) == expected


def test_healthy_slo_never_becomes_slo_impact():
    assert evaluate_exposure(stream_degraded=True, related_slo_failed=False) != ExposureState.SLO_IMPACT_OBSERVED


def test_score_renormalizes_missing_evidence_and_confidence_excludes_criticality():
    assert (
        exposure_score(
            criticality=None,
            relationship_strength=1,
            distance=None,
            stream_severity=None,
            slo_evidence=None,
            source_coverage=0,
        )
        == 66.67
    )
    assert exposure_confidence(binding_strength=0.5, source_coverage=0.5) == 0.5


def test_identity_is_stable_and_scope_specific():
    value = impact_identity("a", "prod", "stream", "orders", "p")
    assert value == impact_identity("a", "prod", "stream", "orders", "p")
    assert value != impact_identity("b", "prod", "stream", "orders", "p")
    assert value != impact_identity("a", "dev", "stream", "orders", "p")


class Item:
    def __init__(self, product_id, tenant_id="a", environment="prod", state="active"):
        self.product_id, self.tenant_id, self.environment, self.state = product_id, tenant_id, environment, state


class Port:
    def list_memberships(self, tenant_id, environment, *, entity_ids, limit):
        return [Item("good"), Item("wrong-tenant", "b"), Item("wrong-env", environment="dev")]

    def list_outputs(self, tenant_id, environment, *, entity_ids, limit):
        return [Item("kafka-output")]


def test_resolver_defends_tenant_and_environment_and_keeps_kafka_output():
    from packages.pathways.product_impact import CanonicalMessagingResource

    values = StreamProductImpactResolver(Port()).resolve_resource_products(
        "a",
        "prod",
        CanonicalMessagingResource(
            messaging_system="kafka", resource_kind="topic", canonical_resource_id="topic:orders"
        ),
    )
    assert [value.product_id for value in values] == ["good", "kafka-output"]


@pytest.mark.parametrize("depth,limit,edges", [(9, 1, 1), (1, 201, 1), (1, 1, 1001)])
def test_hard_bounds(depth, limit, edges):
    with pytest.raises(ValueError):
        StreamProductImpactResolver.bounds(depth=depth, limit=limit, edge_limit=edges)
