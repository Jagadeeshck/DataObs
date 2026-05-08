"""
src/poc/spark_instrumentation.py
─────────────────────────────────
Spark + PySpark instrumentation for the DataObs POC.

Default path: **Elastic APM**. ``SparkApmInstrumentation`` is a thin
context manager that wraps a SparkSession and emits Elastic APM
spans for the overall job and each named stage. Telemetry ships to
the APM Server hosted by the Fleet-managed elastic-agent at
``http://elastic-agent:8200``.

The legacy ``SparkOtelInstrumentation`` class is preserved as a
backwards-compatibility shim that delegates to the APM path so the
pipeline never imports the OpenTelemetry SDK at module load time.
This eliminates the ``NameResolutionError(host='otel-collector')``
warnings that previously appeared when the standalone collector
was missing.

Usage
-----
    from src.poc.apm import build_default_apm
    from src.poc.spark_instrumentation import SparkApmInstrumentation

    apm = build_default_apm()
    apm.start()
    with SparkApmInstrumentation(spark, apm=apm, job_name="my_etl") as sapm:
        with sapm.stage("read_s3"):
            df = spark.read.parquet("s3://...")
        with sapm.stage("transform"):
            df = df.filter(...).withColumn(...)
        sapm.emit_metrics(df, stage="transform")
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

from src.poc.apm import ApmTelemetry, build_default_apm

logger = logging.getLogger(__name__)

# Module-level strong reference to the registered SparkListener.
# The _PythonSparkListener is a Py4J JavaObject proxy: the JVM holds only
# a weak reference; Python's GC is the authoritative owner. If the
# listener is created as a local variable inside _register_spark_listener()
# and the method returns, CPython's reference count immediately drops to
# zero and Py4J tears down the callback channel, producing
#   Py4JException: Error while obtaining a new communication channel
# on every subsequent JVM→Python event. Holding a module-level reference
# keeps the proxy alive for the lifetime of the Spark job.
_listener_instance: Optional[Any] = None


def _py4j_callback_server_active(sc) -> bool:
    """Return True only when the Py4J callback server is actually running."""
    try:
        gw = sc._gateway
        if gw is None:
            return False
        cb = getattr(gw, "callback_server", None) or getattr(gw, "_callback_server", None)
        if cb is None:
            return False
        if hasattr(cb, "is_listening"):
            return bool(cb.is_listening)
        return getattr(cb, "server_socket", None) is not None
    except Exception:
        return False


class SparkApmInstrumentation:
    """
    Context manager that instruments a SparkSession with Elastic APM
    spans + custom labels. No OpenTelemetry SDK is imported.
    """

    def __init__(
        self,
        spark,
        apm: Optional[ApmTelemetry] = None,
        job_name: str = "spark-job",
        extra_labels: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.spark = spark
        self.job_name = job_name
        self.extra_labels = extra_labels or {}
        # Allow callers to share a single APM client; otherwise spin one up.
        self._owns_apm = apm is None
        self.apm: ApmTelemetry = apm or build_default_apm()
        self._job_start_time: float = 0.0
        self._root_ctx: Optional[Any] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def __enter__(self) -> "SparkApmInstrumentation":
        if self._owns_apm:
            self.apm.start()
        self._register_spark_listener()
        self._job_start_time = time.time()
        # Record a top-level span for the whole Spark job. We use a
        # raw stage() rather than a transaction() because the parent
        # pipeline runner has already begun a transaction.
        self._root_ctx = self.apm.span(
            f"spark_job/{self.job_name}",
            span_type="spark.job",
            labels={
                "spark.job.name": self.job_name,
                "spark.master": self.spark.sparkContext.master,
                "spark.app.id": self.spark.sparkContext.applicationId,
                "spark.app.name": self.spark.sparkContext.appName,
                "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "poc"),
                **self.extra_labels,
            },
        )
        self._root_ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self._job_start_time
        if self._root_ctx is not None:
            try:
                self._root_ctx.__exit__(exc_type, exc_val, exc_tb)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[SparkApm] root span __exit__ raised (ignored): %s", exc)
            self._root_ctx = None
        self.apm.label(spark_job_duration_seconds=round(duration, 3))
        if exc_type and self.apm.enabled:
            self.apm.capture_exception()
        if self._owns_apm:
            self.apm.shutdown()
        return False

    # ── Spark Listener bridge ──────────────────────────────────────────────
    def _register_spark_listener(self) -> None:
        global _listener_instance
        sc = self.spark.sparkContext

        if not _py4j_callback_server_active(sc):
            logger.info(
                "[SparkApm] Py4J callback server not active — "
                "skipping JVM SparkListener registration. APM spans remain "
                "active via Python stage() context managers."
            )
            return

        try:
            jsc = sc._jsc

            class _PythonSparkListener:
                def onJobStart(self, job_start):  # noqa: N802
                    try:
                        logger.debug("[SparkApm] Job started: %s", job_start.jobId())
                    except Exception as exc:
                        logger.debug("[SparkApm] onJobStart error (ignored): %s", exc)

                def onJobEnd(self, job_end):  # noqa: N802
                    try:
                        logger.debug(
                            "[SparkApm] Job ended: %s → %s",
                            job_end.jobId(), job_end.jobResult(),
                        )
                    except Exception as exc:
                        logger.debug("[SparkApm] onJobEnd error (ignored): %s", exc)

                def onStageCompleted(self, stage_completed):  # noqa: N802
                    try:
                        info = stage_completed.stageInfo()
                        logger.debug(
                            "[SparkApm] Stage %s (attempt %s) completed — %s tasks",
                            info.stageId(), info.attemptNumber(), info.numTasks(),
                        )
                    except Exception as exc:
                        logger.debug("[SparkApm] onStageCompleted error (ignored): %s", exc)

                def onTaskStart(self, task_start):  # noqa: N802
                    pass

                def onTaskEnd(self, task_end):  # noqa: N802
                    pass

                class Java:
                    implements = ["org.apache.spark.scheduler.SparkListenerInterface"]

            listener = _PythonSparkListener()
            _listener_instance = listener
            jsc.sc().addSparkListener(listener)
            logger.info("[SparkApm] SparkListener registered via Py4J (GC-safe reference held)")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[SparkApm] SparkListener registration skipped (%s) — "
                "APM spans still active via Python context managers", exc,
            )

    # ── Public API ─────────────────────────────────────────────────────────
    @contextmanager
    def stage(
        self,
        stage_name: str,
        labels: Optional[Dict[str, Any]] = None,
    ) -> Iterator[None]:
        t0 = time.time()
        merged = {
            "spark.stage.name": stage_name,
            "spark.job.name": self.job_name,
            **(labels or {}),
        }
        try:
            with self.apm.span(
                f"spark_stage/{stage_name}",
                span_type="spark.stage",
                labels=merged,
            ):
                yield
        finally:
            duration = round(time.time() - t0, 3)
            self.apm.label(**{f"stage_duration_seconds.{stage_name}": duration})

    def emit_metrics(
        self,
        df_or_rdd,
        stage: str = "unknown",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            attrs = {
                "spark.stage.name": stage,
                "spark.job.name": self.job_name,
                **(extra or {}),
            }
            try:
                row_count = df_or_rdd.count()
                attrs[f"spark.rows.{stage}"] = row_count
                logger.info("[SparkApm] Stage '%s': %d rows", stage, row_count)
            except Exception:
                pass
            try:
                part_count = df_or_rdd.rdd.getNumPartitions()
                attrs[f"spark.partitions.{stage}"] = part_count
            except Exception:
                pass
            self.apm.label(**attrs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SparkApm] emit_metrics failed: %s", exc)


# ── Backwards-compatibility shim ────────────────────────────────────────────
# Older code (and tests) used SparkOtelInstrumentation. We keep the name as an
# alias of the APM-backed instrumentation so existing imports keep working
# without pulling the OTel SDK into the import path.
class SparkOtelInstrumentation(SparkApmInstrumentation):
    """Deprecated alias — delegates to :class:`SparkApmInstrumentation`."""

    def __init__(
        self,
        spark,
        job_name: str = "spark-job",
        otel_endpoint: Optional[str] = None,  # accepted for API compat, ignored
        extra_resource: Optional[Dict[str, Any]] = None,
    ) -> None:
        if otel_endpoint:
            logger.debug(
                "[SparkOtel] otel_endpoint=%s ignored — POC uses Elastic APM by default",
                otel_endpoint,
            )
        super().__init__(
            spark,
            apm=None,
            job_name=job_name,
            extra_labels=extra_resource or {},
        )
