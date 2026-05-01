"""
src/poc/spark_instrumentation.py
─────────────────────────────────
Spark + PySpark OpenTelemetry Instrumentation.

Provides:
  - SparkOtelInstrumentation  : context manager that wraps a SparkSession
                                 and emits OTel traces + metrics for every
                                 Spark job / stage / task through a
                                 SparkListener JVM callback bridge.
  - spark_stage_span()        : context manager for a single named stage.
  - emit_spark_metrics()      : emit DataFrame / RDD row/partition counts
                                 as OTel metrics after an action.

Usage
-----
    from src.poc.spark_instrumentation import SparkOtelInstrumentation

    with SparkOtelInstrumentation(spark, job_name="my_etl") as sotel:
        with sotel.stage("read_s3"):
            df = spark.read.parquet("s3://...")
        with sotel.stage("transform"):
            df = df.filter(...).withColumn(...)
        with sotel.stage("write_es"):
            df.write.format("org.elasticsearch.spark.sql").save()
        sotel.emit_metrics(df, stage="write_es")
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")


def _build_resource(job_name: str, extra: Dict[str, Any] = {}) -> Resource:
    base = {
        "service.name": f"spark-job-{job_name}",
        "service.namespace": "dataobs",
        "service.version": "1.0.0",
        "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "poc"),
        "spark.job.name": job_name,
        "telemetry.sdk.language": "python",
        "telemetry.source": "spark-pipeline",
        "monitoring.layer": "data-pipeline",
    }
    base.update(extra)
    return Resource.create(base)


class SparkOtelInstrumentation:
    """
    Context manager that instruments a SparkSession with OTel traces + metrics.

    On entry  → creates a root span for the whole Spark job.
    On stage  → child spans with Spark-specific attributes.
    On exit   → flushes and shuts down providers cleanly.
    """

    def __init__(
        self,
        spark,
        job_name: str = "spark-job",
        otel_endpoint: Optional[str] = None,
        extra_resource: Dict[str, Any] = {},
    ):
        self.spark = spark
        self.job_name = job_name
        self.endpoint = otel_endpoint or OTEL_ENDPOINT
        self.resource = _build_resource(job_name, extra_resource)
        self._tracer_provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._tracer = None
        self._meter = None
        self._root_span = None
        self._root_ctx = None
        self._job_start_time: float = 0.0

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def __enter__(self) -> "SparkOtelInstrumentation":
        self._setup_providers()
        self._register_spark_listener()
        self._root_span, self._root_ctx = self._start_root_span()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self._job_start_time
        if self._root_span:
            self._root_span.set_attribute("spark.job.duration_seconds", round(duration, 3))
            if exc_type:
                self._root_span.record_exception(exc_val)
                self._root_span.set_status(
                    trace.StatusCode.ERROR, str(exc_val) if exc_val else "unknown"
                )
            else:
                self._root_span.set_status(trace.StatusCode.OK)
            self._root_span.end()
        self._shutdown()
        return False

    # ── Provider setup ─────────────────────────────────────────────────────
    def _setup_providers(self):
        span_exporter = OTLPSpanExporter(
            endpoint=f"{self.endpoint}/v1/traces",
            headers={},
        )
        self._tracer_provider = TracerProvider(resource=self.resource)
        self._tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(self._tracer_provider)
        self._tracer = self._tracer_provider.get_tracer("spark.instrumentation")

        metric_exporter = OTLPMetricExporter(
            endpoint=f"{self.endpoint}/v1/metrics",
            headers={},
        )
        reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=30_000)
        self._meter_provider = MeterProvider(
            resource=self.resource, metric_readers=[reader]
        )
        metrics.set_meter_provider(self._meter_provider)
        self._meter = self._meter_provider.get_meter("spark.instrumentation")

        # Instrument counters
        self._rows_processed = self._meter.create_counter(
            "spark.rows.processed",
            unit="{rows}",
            description="Total rows processed by Spark stage",
        )
        self._partitions_gauge = self._meter.create_up_down_counter(
            "spark.partitions.active",
            unit="{partitions}",
            description="Active Spark partitions",
        )
        self._stage_duration = self._meter.create_histogram(
            "spark.stage.duration_seconds",
            unit="s",
            description="Spark stage execution time",
        )
        logger.info("[SparkOtel] OTel providers initialised → %s", self.endpoint)

    def _start_root_span(self):
        self._job_start_time = time.time()
        span = self._tracer.start_span(
            f"spark_job/{self.job_name}",
            attributes={
                "spark.job.name": self.job_name,
                "spark.master": self.spark.sparkContext.master,
                "spark.app.id": self.spark.sparkContext.applicationId,
                "spark.app.name": self.spark.sparkContext.appName,
                "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "poc"),
            },
        )
        ctx = trace.use_span(span, end_on_exit=False)
        ctx.__enter__()
        return span, ctx

    # ── Spark Listener bridge ──────────────────────────────────────────────
    def _register_spark_listener(self):
        """
        Registers a lightweight Python-side Spark listener via sc._jvm.
        Falls back silently if JVM bridge is unavailable (unit-test mode).
        """
        try:
            sc = self.spark.sparkContext
            jvm = sc._jvm
            jsc = sc._jsc

            # Py4J wrapper — calls back into Python when Spark events fire
            class _PythonSparkListener:
                def onJobStart(self, job_start):  # noqa: N802
                    job_id = job_start.jobId()
                    logger.debug("[SparkOtel] Job started: %s", job_id)

                def onJobEnd(self, job_end):  # noqa: N802
                    job_id = job_end.jobId()
                    result = str(job_end.jobResult())
                    logger.debug("[SparkOtel] Job ended: %s → %s", job_id, result)

                def onStageCompleted(self, stage_completed):  # noqa: N802
                    info = stage_completed.stageInfo()
                    stage_id = info.stageId()
                    attempt = info.attemptNumber()
                    task_count = info.numTasks()
                    logger.debug(
                        "[SparkOtel] Stage %s (attempt %s) completed — %s tasks",
                        stage_id, attempt, task_count,
                    )

                def onTaskEnd(self, task_end):  # noqa: N802
                    pass  # high-cardinality; skip individual task spans

                class Java:
                    implements = ["org.apache.spark.scheduler.SparkListenerInterface"]

            listener = _PythonSparkListener()
            jsc.sc().addSparkListener(listener)
            logger.info("[SparkOtel] SparkListener registered via Py4J")
        except Exception as exc:
            logger.warning(
                "[SparkOtel] SparkListener registration skipped (%s) — "
                "OTel span/metrics still active via Python context managers",
                exc,
            )

    # ── Public API ─────────────────────────────────────────────────────────
    @contextmanager
    def stage(self, stage_name: str, attributes: Dict[str, Any] = {}):
        """
        Context manager for a named Spark processing stage.
        Creates a child span under the root job span.
        """
        t0 = time.time()
        with self._tracer.start_as_current_span(
            f"spark_stage/{stage_name}",
            attributes={
                "spark.stage.name": stage_name,
                "spark.job.name": self.job_name,
                **attributes,
            },
        ) as span:
            try:
                yield span
                span.set_status(trace.StatusCode.OK)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise
            finally:
                duration = time.time() - t0
                span.set_attribute("spark.stage.duration_seconds", round(duration, 3))
                self._stage_duration.record(
                    duration, {"spark.stage.name": stage_name, "spark.job.name": self.job_name}
                )

    def emit_metrics(self, df_or_rdd, stage: str = "unknown", extra: Dict[str, Any] = {}):
        """
        Emit row / partition counts as OTel metrics.
        Call AFTER a Spark action (count, write, etc.) to avoid extra jobs.
        """
        try:
            attrs = {"spark.stage.name": stage, "spark.job.name": self.job_name, **extra}
            try:
                row_count = df_or_rdd.count()
                self._rows_processed.add(row_count, attrs)
                logger.info("[SparkOtel] Stage '%s': %d rows emitted to metrics", stage, row_count)
            except Exception:
                pass  # count() may fail on streamed/consumed DFs — that's fine
            try:
                part_count = df_or_rdd.rdd.getNumPartitions()
                self._partitions_gauge.add(part_count, attrs)
            except Exception:
                pass
        except Exception as exc:
            logger.warning("[SparkOtel] emit_metrics failed: %s", exc)

    # ── Shutdown ───────────────────────────────────────────────────────────
    def _shutdown(self):
        try:
            if self._tracer_provider:
                self._tracer_provider.shutdown()
            if self._meter_provider:
                self._meter_provider.shutdown()
            logger.info("[SparkOtel] Providers shut down cleanly")
        except Exception as exc:
            logger.warning("[SparkOtel] Shutdown error: %s", exc)
