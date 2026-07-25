from datetime import datetime, timezone

import pytest

from packages.domain_model.monitor import (
    MonitorDefinition,
    MonitorState,
    MonitorTarget,
    MonitorThresholdPolicy,
    MonitorType,
    ThresholdMode,
)
from services.monitoring.definition_service import DefinitionService, IllegalTransition
from services.monitoring.providers.postgres_aggregate import Aggregate, AggregateExpression, compile_expression
from services.monitoring.repository import VersionConflict


class Repo:
    def __init__(self):
        self.value = None
        self.events = []

    def get_monitor(self, tenant_id, environment, monitor_id):
        return (
            self.value
            if self.value
            and (self.value.tenant_id, self.value.environment, self.value.id) == (tenant_id, environment, monitor_id)
            else None
        )

    def create_monitor(self, monitor):
        self.value = monitor
        return monitor

    def update_monitor(self, monitor, *, expected_etag):
        if self.value.etag != expected_etag:
            raise VersionConflict()
        self.value = monitor
        return monitor

    def append_definition_event(self, monitor, *, actor, action):
        self.events.append((monitor.revision, actor, action))


def monitor(tenant="t"):
    return MonitorDefinition(
        id="m",
        tenant_id=tenant,
        monitor_type=MonitorType.VOLUME,
        target=MonitorTarget(asset_id="a"),
        threshold=MonitorThresholdPolicy(mode=ThresholdMode.FIXED, minimum=1),
        managed_by="test",
        etag="",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_etag_transition_and_history():
    repo = Repo()
    service = DefinitionService(repo)
    created = service.create(monitor(), actor="alice")
    changed = service.transition("t", "default", "m", MonitorState.ENABLED, if_match=created.etag, actor="alice")
    assert changed.revision == 2 and changed.etag != created.etag
    assert repo.events == [(1, "alice", "created"), (2, "alice", "updated")]
    with pytest.raises(IllegalTransition):
        service.transition("t", "default", "m", MonitorState.DRAFT, if_match=changed.etag, actor="alice")


def test_postgres_compiler_never_accepts_sql_identifiers():
    assert (
        compile_expression(AggregateExpression(Aggregate.NULL_COUNT, "public", "orders", "email"))
        == 'SELECT /* dataobs-monitor */ COUNT(*) FILTER (WHERE "email" IS NULL) FROM "public"."orders"'
    )
    with pytest.raises(ValueError):
        compile_expression(AggregateExpression(Aggregate.COUNT, "public", "orders; DROP TABLE users"))
    with pytest.raises(ValueError):
        compile_expression(
            AggregateExpression(Aggregate.DISTINCT_COUNT, "public", "orders", "customer", distinct_limit=10001)
        )
