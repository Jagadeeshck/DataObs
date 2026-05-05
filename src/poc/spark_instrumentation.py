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

# FIX 2: Changed hardcoded 'http://otel-collector:4318' default to 'http://localhost:4318'.
# 'otel-collector' is a Docker Compose service-name that is only DNS-resolvable inside
# Docker networking. On EMR, bare EC2, or local runs it produces:
#   NameResolutionError: Failed to resolve 'otel-collector' [Errno -2] Name or service not known
# with continuous OTLP retry/backoff warnings flooding the logs.
# Use OTEL_EXPORTER_OTLP_ENDPOINT env var to override in all environments.
OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

# FIX 2 (supplementary): honour OTEL_SDK_DISABLED to fully suppress OTel export
# in environments where no collector is reachable (e.g. EMR bootstrap, unit tests).
_OTEL_DISABLED = os.environ.get("OTEL_SDK_DISABLED", "false").lower() == "true"

# FIX 1: Module-level strong reference to the registered SparkListener.
# The _PythonSparkListener is a Py4J JavaObject proxy: the JVM holds only
# a weak reference; Python's GC is the authoritative owner.  If the listener
# is created as a local variable inside _register_spark_listener() and the
# method returns, CPython's reference count immediately drops to zero,
# CPython garbage-collects the object, Py4J tears down the callback channel,
# and every subsequent JVM→Python event fires:
#   Py4JException: Error while obtaining a new communication channel
#   Caused by: java.net.ConnectException: Connection refused
# Keeping a module-level reference prevents that.
_listener_instance: Optional[Any] = None


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


def _py4j_callback_server_active(sc) -> bool:
    """
    Return True only when the Py4J callback server is actually running
    and listening.

    Inside `docker compose run --rm pipeline` the GatewayServer callback
    thread may never start (depends on PySpark version and JVM config),
    causing Connection-refused errors on every JVM→Python event callback.
    We guard against that here rather than letting Spark's AsyncEventQueue
    log dozens of Py4JException stack traces.
    """
    try:
        gw = sc._gateway
        if gw is None:
            return False
        # py4j >= 0.10.9 exposes callback_server; older versions expose _callback_server
        cb = getattr(gw, "callback_server", None) or getattr(gw, "_callback_server", None)
        if cb is None:
            return False
        # The server object exists but may not be listening yet.
        # py4j >= 0.10.9.7 exposes an is_listening flag; fall back to
        # checking server_socket for older releases.
        if hasattr(cb, "is_listening"):
            return bool(cb.is_listening)
        return getattr(cb, "server_socket", None) is not None
    except Exception:
        return False


class SparkOtelInstrumentation:
    """
    Context manager that instruments a SparkSession with OTel traces + metrics.

    On entry  → creates a root span for the whole Spark job.
    On stage  → child spans with Spark-specific attributes.
    On exit   → flushes and shuts down providers cleanly.

    Py4J JVM listener
    -----------------
    Registered only when the Py4J callback server socket is confirmed active.
    Every callback is wrapped in an isolated try/except so that a transient
    channel error (Connection refused) is logged at DEBUG level and never
    propagates into Spark's AsyncEventQueue dispatch loop.
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
        if not _OTEL_DISABLED:
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
        tracer = self._tracer or trace.get_tracer("spark.instrumentation")
        span = tracer.start_span(
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

        Guard: only registers when the Py4J callback server socket is
        confirmed active.  If unavailable (common in `docker compose run`
        without an explicit callback port) the listener is skipped and
        instrumentation continues via Python-side stage() context managers.

        FIX 1: The listener object is stored at module level in
        _listener_instance to prevent Python GC from destroying the Py4J
        proxy before Spark's AsyncEventQueue has finished dispatching events.
        Losing the Python-side reference causes:
          Py4JException: Error while obtaining a new communication channel
          Caused by: java.net.ConnectException: Connection refused
        on every onTaskStart / onTaskEnd callback.

        Each callback is wrapped in an isolated try/except so a transient
        Connection-refused error is swallowed at DEBUG level and never
        bubbles up into Spark's AsyncEventQueue dispatch loop.
        """
        global _listener_instance
        sc = self.spark.sparkContext

        if not _py4j_callback_server_active(sc):
            logger.info(
                "[SparkOtel] Py4J callback server not active — "
                "skipping JVM SparkListener registration. "
                "OTel span/metrics remain active via Python stage() context managers."
            )
            return

        try:
            jsc = sc._jsc

            # Py4J wrapper — calls back into Python when Spark events fire.
            # IMPORTANT: every handler is wrapped in try/except so that a
            # broken callback channel never propagates to the JVM event bus.
            class _PythonSparkListener:
                def onJobStart(self, job_start):  # noqa: N802
                    try:
                        job_id = job_start.jobId()
                        logger.debug("[SparkOtel] Job started: %s", job_id)
                    except Exception as exc:
                        logger.debug("[SparkOtel] onJobStart callback error (ignored): %s", exc)

                def onJobEnd(self, job_end):  # noqa: N802
                    try:
                        job_id = job_end.jobId()
                        result = str(job_end.jobResult())
                        logger.debug("[SparkOtel] Job ended: %s → %s", job_id, result)
                    except Exception as exc:
                        logger.debug("[SparkOtel] onJobEnd callback error (ignored): %s", exc)

                def onStageCompleted(self, stage_completed):  # noqa: N802
                    try:
                        info = stage_completed.stageInfo()
                        stage_id = info.stageId()
                        attempt = info.attemptNumber()
                        task_count = info.numTasks()
                        logger.debug(
                            "[SparkOtel] Stage %s (attempt %s) completed — %s tasks",
                            stage_id, attempt, task_count,
                        )
                    except Exception as exc:
                        logger.debug(
                            "[SparkOtel] onStageCompleted callback error (ignored): %s", exc
                        )

                def onTaskStart(self, task_start):  # noqa: N802
                    # High-cardinality; swallow silently to avoid log spam.
                    try:
                        pass
                    except Exception:
                        pass

                def onTaskEnd(self, task_end):  # noqa: N802
                    # High-cardinality; skip individual task spans.
                    try:
                        pass
                    except Exception:
                        pass

                class Java:
                    implements = ["org.apache.spark.scheduler.SparkListenerInterface"]

            listener = _PythonSparkListener()
            # FIX 1: Assign to module-level variable BEFORE registering with the JVM.
            # This guarantees the Python object outlives the registration call and
            # remains alive for the entire duration of the Spark job.
            _listener_instance = listener
            jsc.sc().addSparkListener(listener)
            logger.info("[SparkOtel] SparkListener registered via Py4J (GC-safe reference held)")
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
        tracer = self._tracer or trace.get_tracer("spark.instrumentation")
        with tracer.start_as_current_span(
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
                if self._stage_duration:
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
                if self._rows_processed:
                    self._rows_processed.add(row_count, attrs)
                logger.info("[SparkOtel] Stage '%s': %d rows emitted to metrics", stage, row_count)
            except Exception:
                pass  # count() may fail on streamed/consumed DFs — that's fine
            try:
                part_count = df_or_rdd.rdd.getNumPartitions()
                if self._partitions_gauge:
                    self._partitions_gauge.add(part_count, attrs)
            except Exception:
                pass
        except Exception as exc:
            logger.warning("[SparkOtel] emit_metrics failed: %s", exc)

    # ── Shutdown ───────────────────────────────────────────────────────────
    def _shutdown(self):
        global _listener_instance
        try:
            if self._tracer_provider:
                self._tracer_provider.shutdown()
            if self._meter_provider:
                self._meter_provider.shutdown()
            logger.info("[SparkOtel] Providers shut down cleanly")
        except Exception as exc:
            logger.warning("[SparkOtel] Shutdown error: %s", exc)
        finally:
            # Release the strong reference after shutdown; the JVM listener
            # is no longer needed once the job completes.
            _listener_instance = None
