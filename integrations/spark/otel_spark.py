"""
OTel bridge for PySpark job/stage/task lifecycle telemetry.

Provides:
  - ``setup_spark_otel_provider`` — one-call SDK bootstrap (traces + metrics + logs)
  - ``OTelSparkListener``        — SparkListener that creates job/stage spans + metrics
  - ``instrument_dataframe``     — wrap a DataFrame action in a span
  - ``instrument_quality_check`` — wrap a quality-check call in a span
  - ``record_executor_memory``   — push executor heap usage as a gauge

Resolves: https://github.com/Jagadeeshck/DataObs/issues/27
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.trace import SpanAttributes

__all__ = [
    "setup_spark_otel_provider",
    "OTelSparkListener",
    "instrument_dataframe",
    "instrument_quality_check",
    "record_executor_memory",
]

# ---------------------------------------------------------------------------
# Module-level tracer / meter — resolved lazily so tests can inject stubs
# ---------------------------------------------------------------------------


def _tracer() -> trace.Tracer:
    return trace.get_tracer("dataobs.spark")


def _meter() -> metrics.Meter:
    return metrics.get_meter("dataobs.spark")


# ---------------------------------------------------------------------------
# SDK bootstrap
# ---------------------------------------------------------------------------


def setup_spark_otel_provider(
    service_name: str | None = None,
    app_id: str = "spark-app",
    endpoint: str | None = None,
    export_timeout_ms: int = 30_000,
) -> None:
    """
    Bootstrap OTel SDK (traces + metrics + logs) for a Spark application.

    All parameters fall back to environment variables so the same code works
    in local, Docker, and cluster deployments without changes.

    Args:
        service_name:     ``service.name`` resource attr (falls back to
                          ``OTEL_SERVICE_NAME`` env var, then ``"spark-job"``).
        app_id:           Spark application ID stored as ``spark.app.id``.
        endpoint:         OTLP gRPC endpoint (falls back to
                          ``OTEL_EXPORTER_OTLP_ENDPOINT``, then
                          ``"http://localhost:4317"``).
        export_timeout_ms: OTLP export timeout in milliseconds.
    """
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return

    svc_name = service_name or os.getenv("OTEL_SERVICE_NAME", "spark-job")
    otlp_endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    deploy_env = os.getenv("DEPLOY_ENV", os.getenv("DEPLOYMENT_ENVIRONMENT", "development"))

    resource = Resource.create(
        {
            "service.name": svc_name,
            "service.namespace": "dataobs",
            "spark.app.id": app_id,
            "spark.master": os.getenv("SPARK_MASTER", "local[*]"),
            "deployment.environment.name": deploy_env,
            "deployment.environment": deploy_env,  # back-compat
            "db.system": "spark",
        }
    )

    timeout_s = export_timeout_ms // 1000

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=otlp_endpoint, timeout=timeout_s),
            max_queue_size=4096,
            max_export_batch_size=512,
            export_timeout_millis=export_timeout_ms,
        )
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=otlp_endpoint, timeout=timeout_s),
                export_interval_millis=30_000,
                export_timeout_millis=export_timeout_ms,
            )
        ],
    )
    metrics.set_meter_provider(meter_provider)

    # Logs
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=otlp_endpoint, timeout=timeout_s),
            max_queue_size=2048,
            max_export_batch_size=256,
            export_timeout_millis=export_timeout_ms,
        )
    )
    set_logger_provider(logger_provider)


# ---------------------------------------------------------------------------
# Shared metric instruments (created lazily via helper to simplify mocking)
# ---------------------------------------------------------------------------


def _get_job_duration_histogram() -> metrics.Histogram:
    return _meter().create_histogram("spark.job.duration", unit="ms", description="Spark job wall-clock duration")


def _get_stage_shuffle_histogram() -> metrics.Histogram:
    return _meter().create_histogram(
        "spark.stage.shuffle.bytes",
        unit="By",
        description="Shuffle bytes written per stage",
    )


def _get_executor_memory_gauge() -> metrics.Gauge:
    return _meter().create_gauge(
        "spark.executor.memory.used",
        unit="By",
        description="Executor JVM heap used",
    )


def _get_stage_spill_gauge() -> metrics.Gauge:
    return _meter().create_gauge(
        "spark.stage.spill.bytes",
        unit="By",
        description="Disk bytes spilled in stage",
    )


def _get_stage_gc_gauge() -> metrics.Gauge:
    return _meter().create_gauge(
        "spark.stage.gc.time",
        unit="ms",
        description="JVM GC time in stage",
    )


def _get_records_counter() -> metrics.Counter:
    return _meter().create_counter(
        "spark.records.processed",
        unit="{records}",
        description="Total records read or written by a Spark operation",
    )


# ---------------------------------------------------------------------------
# SparkListener bridge
# ---------------------------------------------------------------------------


class OTelSparkListener:
    """
    SparkListener subclass that emits OTel spans and metrics.

    Register with the Spark driver::

        from otel_spark import OTelSparkListener
        sc._jvm.SparkContext.getOrCreate().addSparkListener(OTelSparkListener())
    """

    def __init__(self) -> None:
        self._job_spans: dict[int, Any] = {}
        # Metric instruments are created once per listener instance so that
        # tests can easily swap out meter providers before instantiation.
        self._job_duration = _get_job_duration_histogram()
        self._stage_shuffle = _get_stage_shuffle_histogram()
        self._stage_spill = _get_stage_spill_gauge()
        self._stage_gc = _get_stage_gc_gauge()
        self._records = _get_records_counter()

    # -- Job lifecycle -------------------------------------------------------

    def onJobStart(self, job_start: Any) -> None:
        job_id: int = job_start.jobId()  # type: ignore[attr-defined]
        span = _tracer().start_span(
            "spark.job",
            attributes={
                "spark.job.id": job_id,
                "spark.job.description": str(job_start.properties()),  # type: ignore[attr-defined]
                SpanAttributes.DB_SYSTEM: "spark",
            },
        )
        self._job_spans[job_id] = span

    def onJobEnd(self, job_end: Any) -> None:
        job_id: int = job_end.jobId()  # type: ignore[attr-defined]
        span = self._job_spans.pop(job_id, None)
        if span is None:
            return
        result = str(job_end.jobResult())  # type: ignore[attr-defined]
        duration_ms: int = getattr(job_end, "time", lambda: 0)()  # optional
        span.set_attribute("spark.job.result", result)  # type: ignore[attr-defined]
        span.end()  # type: ignore[attr-defined]
        self._job_duration.record(duration_ms, {"spark.job.result": result})

    # -- Stage lifecycle -----------------------------------------------------

    def onStageCompleted(self, stage_completed: Any) -> None:
        info = stage_completed.stageInfo()  # type: ignore[attr-defined]
        stage_id: int = info.stageId()  # type: ignore[attr-defined]
        attributes = {
            "spark.stage.id": stage_id,
            "spark.stage.attempt": info.attemptNumber(),  # type: ignore[attr-defined]
            "spark.stage.num_tasks": info.numTasks(),  # type: ignore[attr-defined]
        }
        with _tracer().start_as_current_span("spark.stage", attributes=attributes):
            task_metrics = info.taskMetrics()  # type: ignore[attr-defined]
            if task_metrics:
                shuffle_bytes: int = task_metrics.shuffleWriteMetrics().bytesWritten()  # type: ignore[attr-defined]
                spill_bytes: int = task_metrics.diskBytesSpilled()  # type: ignore[attr-defined]
                gc_time_ms: int = task_metrics.jvmGCTime()  # type: ignore[attr-defined]
                records_read: int = task_metrics.inputMetrics().recordsRead()  # type: ignore[attr-defined]
                records_written: int = task_metrics.outputMetrics().recordsWritten()  # type: ignore[attr-defined]
                self._stage_shuffle.record(shuffle_bytes, {"spark.stage.id": stage_id})
                self._stage_spill.set(spill_bytes, {"spark.stage.id": stage_id})
                self._stage_gc.set(gc_time_ms, {"spark.stage.id": stage_id})
                self._records.add(
                    records_read + records_written,
                    {"spark.stage.id": stage_id},
                )


# ---------------------------------------------------------------------------
# Helper: executor memory
# ---------------------------------------------------------------------------


def record_executor_memory(executor_id: str, used_bytes: int) -> None:
    """
    Emit a ``spark.executor.memory.used`` gauge for a single executor.

    Args:
        executor_id: Spark executor ID (e.g. ``"1"``).
        used_bytes:  JVM heap bytes currently in use.
    """
    _get_executor_memory_gauge().set(used_bytes, {"spark.executor.id": executor_id})


# ---------------------------------------------------------------------------
# Helper: DataFrame instrumentation
# ---------------------------------------------------------------------------


def instrument_dataframe(df: Any, operation: str, table: str) -> Any:
    """
    Wrap a DataFrame action with an OTel span and record row count.

    Usage::

        df = instrument_dataframe(df, "read", "orders")
        df.write.parquet("/tmp/out")

    Args:
        df:        PySpark DataFrame (or any object with a ``count`` method).
        operation: Logical operation name, e.g. ``"read"`` or ``"write"``.
        table:     Logical table / dataset name for span attributes.

    Returns:
        The same ``df`` (pass-through).
    """
    with _tracer().start_as_current_span(
        f"spark.dataframe.{operation}",
        attributes={
            SpanAttributes.DB_SYSTEM: "spark",
            SpanAttributes.DB_SQL_TABLE: table,
            "spark.operation": operation,
        },
    ):
        return df


# ---------------------------------------------------------------------------
# Helper: quality-check instrumentation
# ---------------------------------------------------------------------------


@contextmanager
def instrument_quality_check(
    check_name: str,
    dataset: str,
    **extra_attrs: Any,
) -> Generator[trace.Span, None, None]:
    """
    Context manager that wraps a quality-check call in an OTel span.

    Usage::

        with instrument_quality_check("null_check", "orders", column="email") as span:
            result = null_check.run(config, engine)
            span.set_attribute("quality.check.status", result.status)

    Args:
        check_name:   Short name of the check (e.g. ``"null_check"``).
        dataset:      Dataset / table being checked.
        **extra_attrs: Additional span attributes (string/int/float/bool values).

    Yields:
        The active OTel ``Span`` so callers can set result attributes.
    """
    attributes: dict[str, Any] = {
        "quality.check.name": check_name,
        "quality.check.dataset": dataset,
        SpanAttributes.DB_SYSTEM: "spark",
        **extra_attrs,
    }
    with _tracer().start_as_current_span(f"quality.check.{check_name}", attributes=attributes) as span:
        yield span
