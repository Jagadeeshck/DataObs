"""
Tests for integrations/spark OTel instrumentation.

All Spark / JVM dependencies are mocked so the suite runs without PySpark
or a real OTel Collector.  Tests cover:

  - ``OTelSparkListener`` job/stage lifecycle → span creation and attributes
  - ``instrument_dataframe`` → span attributes
  - ``instrument_quality_check`` → span attributes and pass-through
  - ``record_executor_memory`` → gauge call
  - ``setup_spark_otel_provider`` → SDK wiring (no-op when disabled)
"""

from __future__ import annotations

import sys
import types

# ---------------------------------------------------------------------------
# Ensure the integration directory is importable without install.
# ---------------------------------------------------------------------------
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

_SPARK_DIR = Path(__file__).resolve().parents[1] / "integrations" / "spark"
if str(_SPARK_DIR) not in sys.path:
    sys.path.insert(0, str(_SPARK_DIR))

# ---------------------------------------------------------------------------
# Minimal stubs for opentelemetry packages so we can import otel_spark even
# when the SDK is not installed in the CI environment.
# ---------------------------------------------------------------------------


def _ensure_otel_stubs() -> None:
    """Inject lightweight stub modules if the real SDK is absent."""
    try:
        import opentelemetry  # noqa: F401

        return  # real SDK present — no stubs needed
    except ModuleNotFoundError:
        pass

    # Build a minimal fake SDK tree.
    otel_pkg = types.ModuleType("opentelemetry")
    sys.modules.setdefault("opentelemetry", otel_pkg)

    for sub in (
        "opentelemetry.trace",
        "opentelemetry.metrics",
        "opentelemetry._logs",
        "opentelemetry.sdk",
        "opentelemetry.sdk.trace",
        "opentelemetry.sdk.trace.export",
        "opentelemetry.sdk.metrics",
        "opentelemetry.sdk.metrics.export",
        "opentelemetry.sdk.resources",
        "opentelemetry.sdk._logs",
        "opentelemetry.sdk._logs.export",
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter",
        "opentelemetry.exporter.otlp.proto.grpc.metric_exporter",
        "opentelemetry.exporter.otlp.proto.grpc._log_exporter",
        "opentelemetry.semconv.trace",
    ):
        sys.modules.setdefault(sub, types.ModuleType(sub))

    # SpanAttributes stub
    sa = sys.modules["opentelemetry.semconv.trace"]
    if not hasattr(sa, "SpanAttributes"):
        sa.SpanAttributes = types.SimpleNamespace(DB_SYSTEM="db.system", DB_SQL_TABLE="db.sql.table")  # type: ignore


_ensure_otel_stubs()

# ---------------------------------------------------------------------------
# Now import the module under test.
# ---------------------------------------------------------------------------
import otel_spark  # noqa: E402  (after path/stub setup)

# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture()
def noop_span():
    """A span that tracks set_attribute / end calls."""
    span = MagicMock()
    span.__enter__ = lambda s: s
    span.__exit__ = MagicMock(return_value=False)
    return span


@pytest.fixture()
def patched_tracer(noop_span):
    """Patch otel_spark._tracer to return a controllable MagicMock."""
    tracer = MagicMock()
    tracer.start_span.return_value = noop_span
    tracer.start_as_current_span.return_value = noop_span
    with patch.object(otel_spark, "_tracer", return_value=tracer):
        yield tracer


@pytest.fixture()
def patched_meter():
    """Patch otel_spark._meter to return a MagicMock meter."""
    meter = MagicMock()
    # Histogram / counter / gauge all return mocks with .record / .add / .set
    meter.create_histogram.return_value = MagicMock()
    meter.create_counter.return_value = MagicMock()
    meter.create_gauge.return_value = MagicMock()
    with patch.object(otel_spark, "_meter", return_value=meter):
        yield meter


# ===========================================================================
# OTelSparkListener — job lifecycle
# ===========================================================================


def _make_job_start(job_id: int, properties: str = "{}"):
    js = MagicMock()
    js.jobId.return_value = job_id
    js.properties.return_value = properties
    return js


def _make_job_end(job_id: int, result: str = "JobSucceeded", time_ms: int = 500):
    je = MagicMock()
    je.jobId.return_value = job_id
    je.jobResult.return_value = result
    je.time.return_value = time_ms
    return je


class TestOTelSparkListenerJob:
    def test_on_job_start_creates_span(self, patched_tracer, patched_meter):
        listener = otel_spark.OTelSparkListener()
        listener.onJobStart(_make_job_start(job_id=1))

        patched_tracer.start_span.assert_called_once()
        call_kwargs = patched_tracer.start_span.call_args
        assert call_kwargs.args[0] == "spark.job"
        attrs = call_kwargs.kwargs["attributes"]
        assert attrs["spark.job.id"] == 1

    def test_on_job_start_stores_span(self, patched_tracer, patched_meter, noop_span):
        listener = otel_spark.OTelSparkListener()
        listener.onJobStart(_make_job_start(job_id=42))
        assert 42 in listener._job_spans

    def test_on_job_end_ends_span_and_sets_result(self, patched_tracer, patched_meter, noop_span):
        listener = otel_spark.OTelSparkListener()
        listener.onJobStart(_make_job_start(job_id=1))
        listener.onJobEnd(_make_job_end(job_id=1, result="JobSucceeded"))

        noop_span.set_attribute.assert_called_with("spark.job.result", "JobSucceeded")
        noop_span.end.assert_called_once()
        assert 1 not in listener._job_spans

    def test_on_job_end_unknown_job_does_not_raise(self, patched_tracer, patched_meter):
        listener = otel_spark.OTelSparkListener()
        # Should not raise even with no matching start
        listener.onJobEnd(_make_job_end(job_id=999))

    def test_multiple_concurrent_jobs(self, patched_tracer, patched_meter):
        spans = [MagicMock() for _ in range(3)]
        patched_tracer.start_span.side_effect = spans

        listener = otel_spark.OTelSparkListener()
        for i in range(3):
            listener.onJobStart(_make_job_start(job_id=i))

        assert len(listener._job_spans) == 3
        listener.onJobEnd(_make_job_end(job_id=1))
        assert len(listener._job_spans) == 2


# ===========================================================================
# OTelSparkListener — stage lifecycle
# ===========================================================================


def _make_stage_completed(
    stage_id: int = 0,
    attempt: int = 0,
    num_tasks: int = 10,
    shuffle_bytes: int = 1024,
    spill_bytes: int = 0,
    gc_time: int = 50,
    records_read: int = 100,
    records_written: int = 80,
):
    task_metrics = MagicMock()
    task_metrics.shuffleWriteMetrics().bytesWritten.return_value = shuffle_bytes
    task_metrics.diskBytesSpilled.return_value = spill_bytes
    task_metrics.jvmGCTime.return_value = gc_time
    task_metrics.inputMetrics().recordsRead.return_value = records_read
    task_metrics.outputMetrics().recordsWritten.return_value = records_written

    info = MagicMock()
    info.stageId.return_value = stage_id
    info.attemptNumber.return_value = attempt
    info.numTasks.return_value = num_tasks
    info.taskMetrics.return_value = task_metrics

    sc = MagicMock()
    sc.stageInfo.return_value = info
    return sc


class TestOTelSparkListenerStage:
    def test_on_stage_completed_creates_span(self, patched_tracer, patched_meter):
        listener = otel_spark.OTelSparkListener()
        listener.onStageCompleted(_make_stage_completed(stage_id=5))

        patched_tracer.start_as_current_span.assert_called_once()
        span_name = patched_tracer.start_as_current_span.call_args.args[0]
        assert span_name == "spark.stage"

    def test_on_stage_completed_records_shuffle_bytes(self, patched_tracer, patched_meter, noop_span):
        listener = otel_spark.OTelSparkListener()
        listener.onStageCompleted(_make_stage_completed(stage_id=3, shuffle_bytes=8192))

        # _stage_shuffle histogram should have been recorded
        listener._stage_shuffle.record.assert_called_once_with(8192, {"spark.stage.id": 3})

    def test_on_stage_completed_no_task_metrics(self, patched_tracer, patched_meter):
        """Stage without task metrics should not raise."""
        info = MagicMock()
        info.stageId.return_value = 0
        info.attemptNumber.return_value = 0
        info.numTasks.return_value = 5
        info.taskMetrics.return_value = None

        sc = MagicMock()
        sc.stageInfo.return_value = info

        listener = otel_spark.OTelSparkListener()
        listener.onStageCompleted(sc)  # must not raise


# ===========================================================================
# instrument_dataframe
# ===========================================================================


class TestInstrumentDataframe:
    def test_returns_same_df(self, patched_tracer, patched_meter, noop_span):
        patched_tracer.start_as_current_span.return_value = noop_span
        df = object()
        result = otel_spark.instrument_dataframe(df, "read", "orders")
        assert result is df

    def test_span_has_correct_attributes(self, patched_tracer, patched_meter, noop_span):
        patched_tracer.start_as_current_span.return_value = noop_span
        otel_spark.instrument_dataframe(object(), "write", "orders_clean")

        call_kwargs = patched_tracer.start_as_current_span.call_args
        assert call_kwargs.args[0] == "spark.dataframe.write"
        attrs = call_kwargs.kwargs["attributes"]
        assert attrs["spark.operation"] == "write"

    def test_span_name_uses_operation(self, patched_tracer, patched_meter, noop_span):
        patched_tracer.start_as_current_span.return_value = noop_span
        otel_spark.instrument_dataframe(object(), "transform", "events")

        name = patched_tracer.start_as_current_span.call_args.args[0]
        assert name == "spark.dataframe.transform"


# ===========================================================================
# instrument_quality_check
# ===========================================================================


class TestInstrumentQualityCheck:
    def test_yields_span(self, patched_tracer, patched_meter, noop_span):
        patched_tracer.start_as_current_span.return_value = noop_span
        with otel_spark.instrument_quality_check("null_check", "orders") as span:
            assert span is noop_span

    def test_span_has_check_name_and_dataset(self, patched_tracer, patched_meter, noop_span):
        patched_tracer.start_as_current_span.return_value = noop_span
        with otel_spark.instrument_quality_check("uniqueness_check", "customers"):
            pass

        call_kwargs = patched_tracer.start_as_current_span.call_args
        assert call_kwargs.args[0] == "quality.check.uniqueness_check"
        attrs = call_kwargs.kwargs["attributes"]
        assert attrs["quality.check.name"] == "uniqueness_check"
        assert attrs["quality.check.dataset"] == "customers"

    def test_extra_attrs_forwarded(self, patched_tracer, patched_meter, noop_span):
        patched_tracer.start_as_current_span.return_value = noop_span
        with otel_spark.instrument_quality_check("value_range", "orders", column="amount", min_value=0):
            pass

        attrs = patched_tracer.start_as_current_span.call_args.kwargs["attributes"]
        assert attrs["column"] == "amount"
        assert attrs["min_value"] == 0

    def test_exception_propagates(self, patched_tracer, patched_meter, noop_span):
        patched_tracer.start_as_current_span.return_value = noop_span
        with pytest.raises(ValueError, match="bad"):
            with otel_spark.instrument_quality_check("null_check", "orders"):
                raise ValueError("bad")


# ===========================================================================
# record_executor_memory
# ===========================================================================


class TestRecordExecutorMemory:
    def test_calls_gauge_set(self, patched_tracer, patched_meter):
        gauge = MagicMock()
        patched_meter.create_gauge.return_value = gauge

        with patch.object(otel_spark, "_get_executor_memory_gauge", return_value=gauge):
            otel_spark.record_executor_memory(executor_id="3", used_bytes=256 * 1024 * 1024)

        gauge.set.assert_called_once_with(256 * 1024 * 1024, {"spark.executor.id": "3"})


# ===========================================================================
# setup_spark_otel_provider — disabled path
# ===========================================================================


class TestSetupSparkOtelProvider:
    def test_no_op_when_sdk_disabled(self, monkeypatch):
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        # Should return without touching any provider
        with (
            patch("opentelemetry.trace.set_tracer_provider") as mock_trace,
            patch("opentelemetry.metrics.set_meter_provider") as mock_metrics,
        ):
            otel_spark.setup_spark_otel_provider()
            mock_trace.assert_not_called()
            mock_metrics.assert_not_called()

    def test_uses_env_service_name(self, monkeypatch):
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
        monkeypatch.setenv("OTEL_SERVICE_NAME", "test-spark-svc")

        with (
            patch("opentelemetry.trace.set_tracer_provider"),
            patch("opentelemetry.metrics.set_meter_provider"),
            patch("opentelemetry._logs.set_logger_provider"),
            patch("otel_spark.TracerProvider") as mock_tp,
            patch("otel_spark.MeterProvider"),
            patch("otel_spark.LoggerProvider"),
            patch("otel_spark.Resource") as mock_res,
        ):
            mock_res.create.return_value = MagicMock()
            mock_tp.return_value = MagicMock()
            otel_spark.setup_spark_otel_provider()

            resource_attrs = mock_res.create.call_args.args[0]
            assert resource_attrs["service.name"] == "test-spark-svc"
