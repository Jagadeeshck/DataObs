from datetime import datetime, timezone

import pytest

from packages.domain_model.monitor import (
    MonitorBaselinePolicy,
    MonitorDefinition,
    MonitorTarget,
    MonitorThresholdPolicy,
    MonitorType,
    ThresholdMode,
)
from services.monitoring.capabilities import CAPABILITIES, capability_documents, validate_monitor_definition


def definition(monitor_type=MonitorType.VOLUME, *, target=None, mode=ThresholdMode.FIXED, baseline=None):
    return MonitorDefinition(
        id="m1",
        tenant_id="tenant-a",
        environment="prod",
        monitor_type=monitor_type,
        target=target or MonitorTarget(asset_id="asset-a", parameters={"aggregation": "count"}),
        threshold=MonitorThresholdPolicy(mode=mode, maximum=100),
        baseline=baseline,
        managed_by="api",
        etag="v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_registry_is_explicit_and_reports_broad_enum_as_unsupported():
    assert set(CAPABILITIES) == {
        "freshness",
        "volume",
        "schema_change",
        "field_null_rate",
        "field_unique_rate",
        "field_distribution",
        "field_range",
        "validation",
        "custom_sql_aggregate",
    }
    documents = {item["monitor_type"]: item for item in capability_documents()}
    assert documents["volume"]["capability_state"] == "supported"
    assert documents["query_performance"]["capability_state"] == "unsupported"


def test_validation_fails_closed_and_requires_baseline():
    validate_monitor_definition(definition())
    with pytest.raises(ValueError, match="not executable"):
        validate_monitor_definition(definition(MonitorType.QUERY_PERFORMANCE))
    with pytest.raises(ValueError, match="baseline"):
        validate_monitor_definition(definition(mode=ThresholdMode.LEARNED))
    validate_monitor_definition(definition(mode=ThresholdMode.LEARNED, baseline=MonitorBaselinePolicy()))


def test_schedule_rejects_unbounded_or_sub_minute_intervals():
    from packages.domain_model.monitor import MonitorSchedule

    for value in ("30s", "0m", "cron * * * *", "32d"):
        with pytest.raises(ValueError):
            MonitorSchedule(interval=value)
