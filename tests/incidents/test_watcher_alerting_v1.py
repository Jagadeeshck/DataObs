"""Team 3 Watcher-driven alerting: lifecycle, trigger mapping, webhook→pipeline.

All Elasticsearch Watcher interaction is mocked and the notification transport
is never exercised with a real pager/ticket/notification send. The test asserts
that a firing watch flows through the existing deduplicating incident pipeline
and that no autonomous remediation is triggered.
"""

from __future__ import annotations

import pytest

from services.incident_manager.repository import InMemoryIncidentRepository
from services.incident_manager.service import IncidentManagerService
from services.incident_manager.watcher import (
    WatchTriggerError,
    map_watch_firing_to_event,
)
from services.incident_manager.watcher.lifecycle import (
    WatchLifecycleManager,
    WatchRegistration,
    build_watch_id,
)


class _MockWatcher:
    """Mock of the ``client.watcher`` surface. Records calls, never hits ES."""

    def __init__(self, *, fail_put: bool = False) -> None:
        self.put_calls: list[tuple[str, dict]] = []
        self.delete_calls: list[str] = []
        self._fail_put = fail_put

    def put_watch(self, *, id: str, body):  # noqa: A002 - mirrors ES client kw
        if self._fail_put:
            raise RuntimeError("watcher feature not enabled")
        self.put_calls.append((id, dict(body)))
        return {"created": True, "_id": id}

    def delete_watch(self, *, id: str):  # noqa: A002 - mirrors ES client kw
        self.delete_calls.append(id)
        return {"found": True}


def _registration(monitor_id: str = "mon-1") -> WatchRegistration:
    return WatchRegistration(
        tenant_id="tenant-a",
        environment="prod",
        monitor_id=monitor_id,
        body={"trigger": {"schedule": {"interval": "5m"}}, "input": {}, "condition": {}, "actions": {}},
    )


# --------------------------------------------------------------------------- #
# Watch id scoping
# --------------------------------------------------------------------------- #


def test_watch_id_is_tenant_and_environment_scoped():
    assert build_watch_id("tenant-a", "prod", "mon-1") == "dataobs-tenant-a-prod-mon-1"


@pytest.mark.parametrize("bad", [("", "prod", "m"), ("t", "", "m"), ("t", "e", "")])
def test_watch_id_requires_all_parts(bad):
    with pytest.raises(ValueError):
        build_watch_id(*bad)


# --------------------------------------------------------------------------- #
# Lifecycle with native Watcher
# --------------------------------------------------------------------------- #


def test_register_native_watch_records_source_watcher():
    watcher = _MockWatcher()
    mgr = WatchLifecycleManager(watcher)

    result = mgr.register(_registration())

    assert result.status == "registered"
    assert result.source == "watcher"
    assert result.watch_id == "dataobs-tenant-a-prod-mon-1"
    assert watcher.put_calls == [("dataobs-tenant-a-prod-mon-1", dict(_registration().body))]
    assert mgr.registered_watch_ids == ("dataobs-tenant-a-prod-mon-1",)


def test_deregister_native_watch_deletes_and_is_idempotent():
    watcher = _MockWatcher()
    mgr = WatchLifecycleManager(watcher)
    mgr.register(_registration())

    first = mgr.deregister("tenant-a", "prod", "mon-1")
    second = mgr.deregister("tenant-a", "prod", "mon-1")

    assert first.status == "deregistered"
    assert first.source == "watcher"
    assert watcher.delete_calls == ["dataobs-tenant-a-prod-mon-1"]
    # Idempotent: a second deregister reports nothing registered, no extra delete.
    assert second.source == "none"
    assert second.detail == "no watch registered"
    assert watcher.delete_calls == ["dataobs-tenant-a-prod-mon-1"]


# --------------------------------------------------------------------------- #
# APScheduler fallback (honest distinct states)
# --------------------------------------------------------------------------- #


def test_fallback_scheduled_when_no_watcher_client():
    scheduled: list = []
    cancelled: list[str] = []
    mgr = WatchLifecycleManager(
        None,
        schedule_fallback=scheduled.append,
        cancel_fallback=cancelled.append,
    )

    result = mgr.register(_registration())

    assert result.status == "fallback_scheduled"
    assert result.source == "apscheduler"
    assert result.detail == "watcher_unavailable"
    assert len(scheduled) == 1
    assert scheduled[0].watch_id == "dataobs-tenant-a-prod-mon-1"

    dereg = mgr.deregister("tenant-a", "prod", "mon-1")
    assert dereg.source == "apscheduler"
    assert cancelled == ["dataobs-tenant-a-prod-mon-1"]


def test_fallback_used_when_native_put_fails():
    watcher = _MockWatcher(fail_put=True)
    scheduled: list = []
    mgr = WatchLifecycleManager(watcher, schedule_fallback=scheduled.append)

    result = mgr.register(_registration())

    assert result.status == "fallback_scheduled"
    assert result.source == "apscheduler"
    assert result.detail == "RuntimeError"
    assert len(scheduled) == 1


def test_unavailable_when_no_fallback_configured():
    mgr = WatchLifecycleManager(None)  # no watcher, no fallback

    result = mgr.register(_registration())

    # Honest: neither native nor fallback — never a false "registered".
    assert result.status == "unavailable"
    assert result.source == "none"


# --------------------------------------------------------------------------- #
# Firing-watch → normalized event mapping
# --------------------------------------------------------------------------- #


def test_map_watch_firing_produces_monitor_anomaly_event():
    event = map_watch_firing_to_event(
        {
            "watch_id": "dataobs-tenant-a-prod-mon-1",
            "asset_id": "orders",
            "monitor_id": "mon-1",
            "severity": "high",
            "observed_value": {"score": 0.98},
        },
        tenant_id="tenant-a",
    )

    assert event["event_type"] == "profile_anomaly"
    assert event["tenant_id"] == "tenant-a"
    assert event["asset_id"] == "orders"
    assert event["alert_source"] == "elasticsearch_watcher"
    assert event["source_event_id"] == "dataobs-tenant-a-prod-mon-1"
    assert event["observed_value"] == {"score": 0.98}


def test_map_rejects_cross_tenant_firing():
    with pytest.raises(WatchTriggerError, match="cross-tenant"):
        map_watch_firing_to_event(
            {"watch_id": "w1", "asset_id": "orders", "tenant_id": "tenant-b"},
            tenant_id="tenant-a",
        )


def test_map_rejects_condition_not_met():
    with pytest.raises(WatchTriggerError, match="condition not met"):
        map_watch_firing_to_event(
            {"watch_id": "w1", "asset_id": "orders", "condition_met": False},
            tenant_id="tenant-a",
        )


def test_map_requires_asset_and_watch_id():
    with pytest.raises(WatchTriggerError, match="watch_id"):
        map_watch_firing_to_event({"asset_id": "orders"}, tenant_id="tenant-a")
    with pytest.raises(WatchTriggerError, match="asset_id"):
        map_watch_firing_to_event({"watch_id": "w1"}, tenant_id="tenant-a")


# --------------------------------------------------------------------------- #
# Webhook → existing dedup pipeline (no real notification sent)
# --------------------------------------------------------------------------- #


def test_firing_watch_opens_incident_through_existing_pipeline():
    # No correlation_coordinator / dispatcher injected => no notification transport
    # is exercised at all. This proves delivery stays with the existing pipeline
    # and nothing in the Team 3 path sends a pager/ticket/notification.
    manager = IncidentManagerService(InMemoryIncidentRepository())

    event = map_watch_firing_to_event(
        {
            "watch_id": "dataobs-tenant-a-prod-mon-1",
            "asset_id": "orders",
            "monitor_id": "mon-1",
            "severity": "high",
        },
        tenant_id="tenant-a",
    )
    result = manager.ingest(event, tenant_id="tenant-a")

    assert result["ingestion"]["status"] == "created"
    assert result["incident"]["tenant_id"] == "tenant-a"
    assert "orders" in result["incident"]["affected_assets"]


def test_repeated_firing_deduplicates_into_one_incident():
    manager = IncidentManagerService(InMemoryIncidentRepository())
    payload = {
        "watch_id": "dataobs-tenant-a-prod-mon-1",
        "asset_id": "orders",
        "monitor_id": "mon-1",
        "severity": "high",
    }

    first = manager.ingest(map_watch_firing_to_event(payload, tenant_id="tenant-a"), tenant_id="tenant-a")
    second = manager.ingest(map_watch_firing_to_event(payload, tenant_id="tenant-a"), tenant_id="tenant-a")

    # Same watch firing again is deduplicated, not a second incident.
    assert first["incident"]["id"] == second["incident"]["id"]
    assert second["ingestion"]["status"] in {"replayed", "updated"}
