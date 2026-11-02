"""Unit tests for GET /quality/monitors/{id}/ml-detector route handler.

Calls the handler function directly with fake request state (same lightweight
pattern as test_quality_trusted_actor) — no live server or ES needed. Validates
honest states: not_configured when the registry is absent or no detector exists,
and faithful passthrough of a persisted detector record.
"""

from __future__ import annotations

from types import SimpleNamespace

from src.api.monitor_routes import ml_detector


def _request(*, registry, monitor_exists=True, tenant="acme", environment="production"):
    app_state = SimpleNamespace(
        ml_detector_registry=registry,
        monitor_repository=SimpleNamespace(get_monitor=lambda t, e, mid: (object() if monitor_exists else None)),
        settings=SimpleNamespace(environment=environment),
    )
    return SimpleNamespace(
        app=SimpleNamespace(state=app_state),
        state=SimpleNamespace(tenant_id=tenant, request_id="req-1"),
        headers={},
    )


class _FakeRegistry:
    def __init__(self, record):
        self._record = record

    def get(self, tenant, environment, monitor_id):
        return self._record


def test_registry_unavailable_reports_not_configured_unavailable():
    req = _request(registry=None)
    result = ml_detector("mon1", req)
    assert result["detection_mode"] == "manual"
    assert result["provisioning_state"] == "not_configured"
    assert result["availability_state"] == "unavailable"
    assert result["data_status"] == "not_configured"


def test_no_detector_record_reports_not_configured_unknown():
    req = _request(registry=_FakeRegistry(None))
    result = ml_detector("mon1", req)
    assert result["provisioning_state"] == "not_configured"
    assert result["availability_state"] == "unknown"


def test_active_detector_passthrough():
    record = {
        "detection_mode": "auto",
        "ml_job_id": "dataobs-acme-production-mon1",
        "provisioning_state": "active",
        "availability_state": "available",
        "detector_function": "mean",
        "detector_field": "row_count",
        "updated_at": "2026-11-02T00:00:00+00:00",
    }
    req = _request(registry=_FakeRegistry(record))
    result = ml_detector("mon1", req)
    assert result["provisioning_state"] == "active"
    assert result["availability_state"] == "available"
    assert result["ml_job_id"] == "dataobs-acme-production-mon1"
    assert result["detection_mode"] == "auto"


def test_errored_detector_reports_error_never_healthy():
    record = {
        "detection_mode": "auto",
        "ml_job_id": "dataobs-acme-production-mon2",
        "provisioning_state": "error",
        "availability_state": "unavailable",
        "last_error_code": "ml_provisioning_failed",
    }
    req = _request(registry=_FakeRegistry(record))
    result = ml_detector("mon2", req)
    assert result["provisioning_state"] == "error"
    assert result["availability_state"] == "unavailable"
    assert result["last_error_code"] == "ml_provisioning_failed"
