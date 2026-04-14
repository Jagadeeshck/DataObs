"""
OTel bridge for PySpark job/stage/task lifecycle telemetry.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/27
"""
from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.semconv.trace import SpanAttributes

_tracer = trace.get_tracer("dataobs.spark")
_meter = metrics.get_meter("dataobs.spark")

_job_duration = _meter.create_histogram(
    "spark.job.duration", unit="ms", description="Spark job wall-clock duration"
)
_stage_shuffle_bytes = _meter.create_histogram(
    "spark.stage.shuffle.bytes", unit="By", description="Shuffle bytes per stage"
)
_executor_memory = _meter.create_gauge(
    "spark.executor.memory.used", unit="By", description="Executor JVM heap used"
)


class OTelSparkListener:
    """
    SparkListener subclass that emits OTel spans and metrics.

    Usage::

        from otel_spark import OTelSparkListener
        sc._jvm.SparkContext.getOrCreate().addSparkListener(OTelSparkListener())
    """

    def __init__(self) -> None:
        self._job_spans: dict[int, object] = {}
        self._stage_spans: dict[int, object] = {}

    def onJobStart(self, job_start: object) -> None:
        job_id = job_start.jobId()  # type: ignore[attr-defined]
        span = _tracer.start_span(
            "spark.job",
            attributes={
                "spark.job.id": job_id,
                "spark.job.description": str(job_start.properties()),  # type: ignore[attr-defined]
                SpanAttributes.DB_SYSTEM: "spark",
            },
        )
        self._job_spans[job_id] = span

    def onJobEnd(self, job_end: object) -> None:
        job_id = job_end.jobId()  # type: ignore[attr-defined]
        span = self._job_spans.pop(job_id, None)
        if span:
            result = str(job_end.jobResult())  # type: ignore[attr-defined]
            span.set_attribute("spark.job.result", result)  # type: ignore[attr-defined]
            span.end()  # type: ignore[attr-defined]

    def onStageCompleted(self, stage_completed: object) -> None:
        info = stage_completed.stageInfo()  # type: ignore[attr-defined]
        metrics_opt = info.taskMetrics()  # type: ignore[attr-defined]
        with _tracer.start_as_current_span(
            "spark.stage",
            attributes={
                "spark.stage.id": info.stageId(),  # type: ignore[attr-defined]
                "spark.stage.attempt": info.attemptNumber(),  # type: ignore[attr-defined]
                "spark.stage.num_tasks": info.numTasks(),  # type: ignore[attr-defined]
            },
        ):
            if metrics_opt:
                shuffle_bytes = metrics_opt.shuffleWriteMetrics().bytesWritten()  # type: ignore[attr-defined]
                _stage_shuffle_bytes.record(shuffle_bytes, {"spark.stage.id": info.stageId()})  # type: ignore[attr-defined]


def instrument_dataframe(df: object, operation: str, table: str) -> object:
    """
    Wrap a DataFrame action with an OTel span.

    Usage::

        df = instrument_dataframe(df, "read", "orders")
        df.count()
    """
    with _tracer.start_as_current_span(
        f"spark.dataframe.{operation}",
        attributes={
            SpanAttributes.DB_SYSTEM: "spark",
            SpanAttributes.DB_SQL_TABLE: table,
            "spark.operation": operation,
        },
    ):
        return df
