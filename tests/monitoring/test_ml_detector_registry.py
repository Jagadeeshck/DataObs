"""Unit tests for the ML anomaly-detector registry (detection_mode: auto persistence).

Uses an in-memory fake Elasticsearch and a fake ML manager — no live cluster or
X-Pack ML required. Validates honest state transitions, tenant-scoped doc ids,
unsupported-type handling, and idempotent teardown.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pytest

from services.monitoring.ml_detector_registry import (
    ML_DETECTOR_INDEX,
    UNSUPPORTED_REASON,
    MLDetectorRegistry,
    detector_config_for_monitor,
)


class NotFoundError(Exception):
    pass


class _FakeES:
    """Minimal in-memory ES stub: index/get with doc ids."""

    def __init__(self):
        self.docs: dict[tuple[str, str], dict] = {}

    def index(self, index, id, document, refresh=False):
        self.docs[(index, id)] = dict(document)
        return {"result": "created"}

    def get(self, index, id):
        key = (index, id)
        if key not in self.docs:
            raise NotFoundError(id)
        return {"_source": dict(self.docs[key])}


class _FakeML:
    def __init__(self, fail_on=None):
        self.ensured = []
        self.started = []
        self.deleted = []
        self._fail_on = fail_on  # "ensure" | "start" | "delete" | None

    def ensure_job(self, config):
        if self._fail_on == "ensure":
            raise RuntimeError("ml plugin disabled")
        self.ensured.append(config.job_id)

    def start_job(self, job_id, start="now-30d"):
        if self._fail_on == "start":
            raise RuntimeError("datafeed start failed")
        self.started.append(job_id)
        return {"started": True}

    def delete_job(self, job_id):
        if self._fail_on == "delete":
            raise RuntimeError("job absent")
        self.deleted.append(job_id)


class _MT(str, Enum):
    FRESHNESS = "freshness"
    VOLUME = "volume"
    SCHEMA_CHANGE = "schema_change"


@dataclass
class _Monitor:
    id: str
    tenant_id: str
    environment: str
    monitor_type: _MT


# Patch the registry's NotFoundError import to our fake at call sites via monkeypatch.
@pytest.fixture(autouse=True)
def _patch_notfound(monkeypatch):
    import elasticsearch

    monkeypatch.setattr(elasticsearch, "NotFoundError", NotFoundError, raising=False)
    yield


def _registry(fail_on=None):
    es = _FakeES()
    ml = _FakeML(fail_on=fail_on)
    return MLDetectorRegistry(es, ml_manager=ml), es, ml


def test_config_derivation_is_deterministic_and_scoped():
    m = _Monitor("mon1", "acme", "production", _MT.FRESHNESS)
    cfg = detector_config_for_monitor(m)
    assert cfg is not None
    assert cfg.job_id == "dataobs-acme-production-mon1"
    assert cfg.detector_function == "high_mean"
    assert cfg.detector_field == "age_seconds"


def test_unsupported_monitor_type_returns_none():
    m = _Monitor("mon2", "acme", "production", _MT.SCHEMA_CHANGE)
    assert detector_config_for_monitor(m) is None


def test_register_supported_monitor_goes_active():
    reg, es, ml = _registry()
    m = _Monitor("mon1", "acme", "production", _MT.VOLUME)
    record = reg.register(m)

    assert record.provisioning_state == "active"
    assert record.availability_state == "available"
    assert record.configured is True
    assert ml.ensured == ["dataobs-acme-production-mon1"]
    assert ml.started == ["dataobs-acme-production-mon1"]
    # Persisted under a tenant-scoped doc id.
    stored = es.docs[(ML_DETECTOR_INDEX, "acme:production:mon1")]
    assert stored["provisioning_state"] == "active"
    assert stored["detection_mode"] == "auto"


def test_register_unsupported_type_records_error_not_active():
    reg, es, ml = _registry()
    m = _Monitor("mon2", "acme", "production", _MT.SCHEMA_CHANGE)
    record = reg.register(m)

    assert record.provisioning_state == "error"
    assert record.availability_state == "unavailable"
    assert record.configured is False
    assert record.last_error_code == UNSUPPORTED_REASON
    assert ml.ensured == []  # no ML job attempted


def test_register_ml_unavailable_records_error_never_false_active():
    reg, es, ml = _registry(fail_on="start")
    m = _Monitor("mon3", "acme", "production", _MT.FRESHNESS)
    record = reg.register(m)

    # Honest: ML failed to start, so NOT active — recorded as error, not silently healthy.
    assert record.provisioning_state == "error"
    assert record.availability_state == "unavailable"
    assert record.last_error_code == "ml_provisioning_failed"
    stored = es.docs[(ML_DETECTOR_INDEX, "acme:production:mon3")]
    assert stored["provisioning_state"] == "error"


def test_deregister_deletes_job_and_marks_deactivated():
    reg, es, ml = _registry()
    m = _Monitor("mon1", "acme", "production", _MT.VOLUME)
    reg.register(m)

    ok = reg.deregister("acme", "production", "mon1")
    assert ok is True
    assert ml.deleted == ["dataobs-acme-production-mon1"]
    stored = es.docs[(ML_DETECTOR_INDEX, "acme:production:mon1")]
    assert stored["provisioning_state"] == "deactivated"
    assert stored["availability_state"] == "unavailable"


def test_deregister_missing_is_idempotent_false():
    reg, es, ml = _registry()
    assert reg.deregister("acme", "production", "nope") is False
    assert ml.deleted == []


def test_deregister_tolerates_absent_ml_job():
    reg, es, ml = _registry(fail_on="delete")
    m = _Monitor("mon1", "acme", "production", _MT.VOLUME)
    reg.register(m)
    # delete_job raises, but teardown must still mark the record deactivated.
    ok = reg.deregister("acme", "production", "mon1")
    assert ok is True
    stored = es.docs[(ML_DETECTOR_INDEX, "acme:production:mon1")]
    assert stored["provisioning_state"] == "deactivated"


def test_tenant_isolation_in_doc_id():
    reg, es, ml = _registry()
    reg.register(_Monitor("shared", "tenant-a", "production", _MT.VOLUME))
    reg.register(_Monitor("shared", "tenant-b", "production", _MT.VOLUME))
    # Same monitor id, different tenants → distinct records, no collision.
    assert (ML_DETECTOR_INDEX, "tenant-a:production:shared") in es.docs
    assert (ML_DETECTOR_INDEX, "tenant-b:production:shared") in es.docs
    assert reg.get("tenant-a", "production", "shared")["ml_job_id"] == "dataobs-tenant-a-production-shared"
