from datetime import datetime, timedelta, timezone

import pytest

from packages.domain_model.monitor import (
    MonitorDefinition,
    MonitorObservation,
    MonitorTarget,
    MonitorThresholdPolicy,
    MonitorType,
    ThresholdMode,
)
from services.monitoring.baseline_service import build_baseline
from services.monitoring.definition_events import DefinitionOperation
from services.monitoring.evaluation_service import evaluate
from services.monitoring.suppression_service import create_suppression


def monitor(**updates):
    value = MonitorDefinition(
        id="m",
        tenant_id="t",
        environment="prod",
        monitor_type=MonitorType.VOLUME,
        target=MonitorTarget(asset_id="a"),
        threshold=MonitorThresholdPolicy(mode=ThresholdMode.FIXED, minimum=5),
        managed_by="test",
        etag="one",
        **updates
    )
    return value


def test_operation_id_is_deterministic_and_scoped():
    definition = monitor()
    one = DefinitionOperation.build(definition, actor="a", reason="r", action="create")
    two = DefinitionOperation.build(definition, actor="a", reason="r", action="create")
    assert one.operation_id == two.operation_id and one.state == "pending"


def test_baseline_has_no_future_leakage_and_is_deterministic():
    now = datetime.now(timezone.utc)
    old = MonitorObservation(
        monitor_id="m", tenant_id="t", environment="prod", observed_at=now - timedelta(minutes=1), value=10
    )
    future = old.model_copy(update={"observed_at": now + timedelta(minutes=1), "value": 1000})
    one = build_baseline(
        tenant_id="t", environment="prod", monitor_id="m", definition_revision=1, observations=[old, future], as_of=now
    )
    two = build_baseline(
        tenant_id="t", environment="prod", monitor_id="m", definition_revision=1, observations=[old, future], as_of=now
    )
    assert (
        one["sample_count"] == 1
        and one["expected_maximum"] == 10
        and one["baseline_version"] == two["baseline_version"]
    )


def test_missing_provider_never_passes():
    observation = MonitorObservation(monitor_id="m", tenant_id="t", environment="prod", value=10)
    assert evaluate(monitor(), observation, provider_status="unsupported")["state"] == "source_unavailable"


def test_suppression_requires_bounded_approval():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        create_suppression(
            tenant_id="t",
            environment="prod",
            monitor_id="m",
            actor="a",
            reason="r",
            approval_reference="",
            starts_at=now,
            ends_at=now + timedelta(hours=1),
        )
