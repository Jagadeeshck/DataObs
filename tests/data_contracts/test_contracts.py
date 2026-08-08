from dataclasses import replace
from datetime import datetime, timezone

import pytest

from services.data_contracts.evaluator import evaluate_contract
from services.data_contracts.lifecycle import InvalidTransition, ReasonRequired, validate_transition
from services.data_contracts.models import (
    ColumnRule,
    CompatibilityMode,
    ContractVersion,
    DataContract,
    EnforcementMode,
    Evidence,
    LifecycleState,
    QualityRequirement,
)
from services.data_contracts.repository import MemoryContractRepository, OverlappingEffectiveVersion, StaleETag
from services.data_contracts.schema_rules import type_compatibility

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def contract(mode=EnforcementMode.ENFORCE):
    return DataContract(
        "c1",
        "t1",
        "prod",
        "asset-1",
        "postgres/db/public/orders",
        "Orders",
        "Order data",
        "owner",
        "team",
        enforcement_mode=mode,
    )


def version(**changes):
    base = ContractVersion(
        "c1",
        1,
        "r1",
        LifecycleState.ACTIVE,
        NOW,
        None,
        (ColumnRule("id", True, "integer", nullable=False),),
        (QualityRequirement("m1"),),
        freshness_max_age_seconds=60,
        volume_min=0,
        compatibility=CompatibilityMode.STRICT,
    )
    return replace(base, **changes)


def test_lifecycle_and_reasons():
    validate_transition(LifecycleState.DRAFT, LifecycleState.IN_REVIEW)
    with pytest.raises(InvalidTransition):
        validate_transition(LifecycleState.DRAFT, LifecycleState.ACTIVE)
    with pytest.raises(ReasonRequired):
        validate_transition(LifecycleState.IN_REVIEW, LifecycleState.REJECTED)


def test_etag_and_tenant_isolation():
    repo = MemoryContractRepository()
    c = contract()
    repo.create_draft(c, replace(version(), lifecycle_state=LifecycleState.DRAFT))
    updated = repo.update_draft(c, c.etag)
    assert updated.revision == 2
    with pytest.raises(StaleETag):
        repo.update_draft(c, 'W/"1"')
    with pytest.raises(KeyError):
        repo.get_contract("other", "prod", "c1")


def test_overlap_rejected():
    repo = MemoryContractRepository()
    repo.create_draft(contract(), version())
    with pytest.raises(OverlappingEffectiveVersion):
        repo.add_version("t1", "prod", replace(version(), version=2, revision_id="r2"))


@pytest.mark.parametrize(
    ("expected", "observed", "result"),
    [
        ("integer", "long", "widening"),
        ("long", "integer", "narrowing"),
        ("string", "integer", "incompatible"),
        (None, "string", "unknown"),
    ],
)
def test_type_compatibility(expected, observed, result):
    assert type_compatibility(expected, observed) == result


def test_evaluation_detects_schema_quality_freshness_and_preserves_zero():
    evidence = Evidence(
        NOW,
        ({"name": "id", "type": "string", "nullable": True}, {"name": "extra", "type": "string"}),
        {"m1": {"state": "breaching"}},
        100,
        0,
    )
    result = evaluate_contract(contract(), version(), evidence, now=NOW)
    assert result.overall_state == "breaching" and result.components["volume"] == 1.0
    assert {v.reason_code for v in result.violations} >= {
        "type_mismatch",
        "nullability_mismatch",
        "unexpected_field",
        "monitor_state_breach",
        "freshness_age_exceeded",
    }


def test_unavailable_is_not_failure_and_low_confidence_not_compliant():
    result = evaluate_contract(contract(), version(), Evidence(NOW), now=NOW)
    assert result.overall_state == "unknown" and not result.violations and result.score is None


@pytest.mark.parametrize(
    ("mode", "state"),
    [
        (EnforcementMode.OBSERVE, "warning"),
        (EnforcementMode.WARN, "warning"),
        (EnforcementMode.ENFORCE, "breaching"),
        (EnforcementMode.DISABLED, "disabled"),
    ],
)
def test_enforcement_modes(mode, state):
    result = evaluate_contract(
        contract(mode),
        version(quality_requirements=(), freshness_max_age_seconds=None, volume_min=None),
        Evidence(NOW, ()),
        now=NOW,
    )
    assert result.overall_state == state
