"""
tests/test_spark_instrumentation_apm.py
────────────────────────────────────────
Regression tests for the APM-backed Spark instrumentation.

Guards introduced after the SparkOtelInstrumentation -> SparkApmInstrumentation
refactor to ensure:

  1. stage() context manager does not require _stage_duration to be set
     before it is called (the original OTel crash at line 360).
  2. SparkOtelInstrumentation shim source code does not contain a bare
     `self._stage_duration` read without assignment (the original crash site).
  3. Default pipeline mode does not emit otel-collector:4318 to the log.

All Spark / JVM / elasticapm dependencies are mocked so the suite runs
without PySpark, a real APM server, or the OTel SDK installed.
"""
from __future__ import annotations

import logging
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ── Minimal stubs ────────────────────────────────────────────────────────────

def _ensure_elasticapm_stub() -> None:
    if "elasticapm" in sys.modules:
        return
    stub = types.ModuleType("elasticapm")
    stub.Client = MagicMock
    stub.get_client = MagicMock(return_value=None)
    stub.instrument = MagicMock()
    sys.modules["elasticapm"] = stub
    sys.modules["elasticapm.contrib"] = types.ModuleType("elasticapm.contrib")
    sys.modules["elasticapm.contrib.starlette"] = types.ModuleType("elasticapm.contrib.starlette")


_ensure_elasticapm_stub()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_mock_spark():
    sc = MagicMock()
    sc.master = "local[*]"
    sc.applicationId = "app-test-001"
    sc.appName = "DataObs-POC-Test"
    sc._gateway = None  # no Py4J callback server
    spark = MagicMock()
    spark.sparkContext = sc
    return spark


def _make_mock_apm(enabled: bool = False):
    """Return a minimal ApmTelemetry mock that satisfies the context manager protocol."""
    from unittest.mock import MagicMock
    import contextlib

    apm = MagicMock()
    apm.enabled = enabled
    apm.start = MagicMock()
    apm.shutdown = MagicMock()
    apm.capture_exception = MagicMock()
    apm.label = MagicMock()

    # span() must return a context manager
    span_cm = MagicMock()
    span_cm.__enter__ = MagicMock(return_value=None)
    span_cm.__exit__ = MagicMock(return_value=False)
    apm.span = MagicMock(return_value=span_cm)
    return apm


# ── Tests ────────────────────────────────────────────────────────────────────


class TestSparkApmNoOtelDependency:
    """Guards the regression where stage() crashed with AttributeError: _stage_duration."""

    def test_stage_context_manager_does_not_raise(self):
        """SparkApmInstrumentation.stage() must complete without AttributeError."""
        from src.poc.spark_instrumentation import SparkApmInstrumentation

        mock_apm = _make_mock_apm(enabled=False)
        instr = SparkApmInstrumentation(_make_mock_spark(), apm=mock_apm)

        # Must not raise AttributeError on _stage_duration
        with instr.stage("test_stage"):
            pass

    def test_stage_updates_stage_duration(self):
        """After stage() exits, _stage_duration must be a non-negative float."""
        from src.poc.spark_instrumentation import SparkApmInstrumentation

        mock_apm = _make_mock_apm(enabled=False)
        instr = SparkApmInstrumentation(_make_mock_spark(), apm=mock_apm)

        with instr.stage("measure_me"):
            pass

        assert isinstance(instr._stage_duration, float)
        assert instr._stage_duration >= 0.0

    def test_multiple_stages_do_not_raise(self):
        """Multiple consecutive stage() calls must all succeed."""
        from src.poc.spark_instrumentation import SparkApmInstrumentation

        mock_apm = _make_mock_apm(enabled=False)
        instr = SparkApmInstrumentation(_make_mock_spark(), apm=mock_apm)

        for name in ("ingest", "transform", "load"):
            with instr.stage(name):
                pass  # must not raise

    def test_shim_stage_does_not_need_stage_duration_before_call(self):
        """SparkOtelInstrumentation.stage() must work without prior _stage_duration.

        Reproduces the original crash:
          File "/app/src/poc/spark_instrumentation.py", line 360, in stage
            if self._stage_duration:
          AttributeError: 'SparkOtelInstrumentation' object has no attribute '_stage_duration'
        """
        from src.poc.spark_instrumentation import SparkOtelInstrumentation

        mock_apm = _make_mock_apm(enabled=False)
        # Patch build_default_apm so the shim does not try to create a real client
        with patch("src.poc.spark_instrumentation.build_default_apm", return_value=mock_apm):
            instr = SparkOtelInstrumentation(_make_mock_spark(), job_name="test-shim")

        with instr.stage("shim_stage"):
            pass

    def test_shim_source_does_not_contain_bare_stage_duration_read(self):
        """SparkOtelInstrumentation must not contain `if self._stage_duration:` pattern.

        That exact construct was the crash site — it read an attribute that was
        never assigned in the shim's __init__ path.
        """
        import inspect
        from src.poc.spark_instrumentation import SparkOtelInstrumentation

        source = inspect.getsource(SparkOtelInstrumentation)
        # The crash pattern was: `if self._stage_duration:` (read without prior assignment)
        # The fix is: assignment (`self._stage_duration = ...`) is always safe.
        # We allow assignments but not bare conditional reads.
        import re
        bare_reads = re.findall(r"if\s+self\._stage_duration", source)
        assert not bare_reads, (
            "SparkOtelInstrumentation must not contain `if self._stage_duration:` — "
            "this was the original crash site. Use `getattr(self, '_stage_duration', 0.0)` "
            "if a conditional read is needed."
        )

    def test_no_otel_bootstrap_log_in_default_pipeline(self, monkeypatch, caplog):
        """Pipeline must not log otel-collector:4318 in default (OTEL_SDK_DISABLED=true) mode."""
        import logging as _logging

        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        # Force telemetry module reload so _OTEL_DISABLED is re-evaluated
        if "src.poc.telemetry" in sys.modules:
            del sys.modules["src.poc.telemetry"]

        with caplog.at_level(_logging.DEBUG):
            from src.poc.telemetry import TelemetryEmitter
            TelemetryEmitter(service_name="default-test", otlp_endpoint=None)

        combined = " ".join(caplog.messages)
        assert "otel-collector:4318" not in combined, (
            "Default pipeline must never log otel-collector:4318 — "
            "this indicates the OTel SDK bootstrap ran when it should not have."
        )
        assert "OTel bootstrap complete" not in combined
