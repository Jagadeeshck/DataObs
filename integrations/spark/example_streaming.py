"""
Structured Streaming example with OTel instrumentation.

Demonstrates:
  - SDK bootstrap via ``setup_spark_otel_provider``
  - Per-micro-batch spans with record count and lag metrics
  - Quality-check spans inside each micro-batch
  - Graceful shutdown with OTel provider flush

Usage::

    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \\
    OTEL_SERVICE_NAME=spark-streaming-orders \\
    spark-submit integrations/spark/example_streaming.py

    # Override the Kafka source (set these env vars):
    KAFKA_BOOTSTRAP_SERVERS=broker:9092
    KAFKA_TOPIC=orders

Resolves: https://github.com/Jagadeeshck/DataObs/issues/27
"""
from __future__ import annotations

import os
import sys
import time

# Allow running directly without installing as a package.
sys.path.insert(0, os.path.dirname(__file__))

from otel_spark import (
    OTelSparkListener,
    instrument_quality_check,
    setup_spark_otel_provider,
)
from opentelemetry import metrics, trace

_tracer = trace.get_tracer("dataobs.spark.streaming")
_meter = metrics.get_meter("dataobs.spark.streaming")

_batch_records = _meter.create_counter(
    "spark.streaming.records.processed",
    unit="{records}",
    description="Total records processed by micro-batch",
)
_batch_duration = _meter.create_histogram(
    "spark.streaming.batch.duration",
    unit="ms",
    description="Wall-clock time for one micro-batch",
)
_batch_lag = _meter.create_gauge(
    "spark.streaming.batch.lag",
    unit="ms",
    description="Approximate consumer lag (current time − max event timestamp)",
)


def _make_batch_processor(max_null_pct: float = 5.0):
    """
    Return a ``foreachBatch`` callback that instruments each micro-batch.

    Args:
        max_null_pct: Maximum acceptable null percentage for ``amount`` column.
    """

    def _process_batch(batch_df: object, batch_id: int) -> None:
        """Instrumented micro-batch callback."""
        t0 = time.monotonic()

        with _tracer.start_as_current_span(
            "spark.streaming.batch",
            attributes={"spark.streaming.batch.id": batch_id},
        ) as span:
            row_count: int = batch_df.count()  # type: ignore[attr-defined]
            span.set_attribute("spark.streaming.batch.row_count", row_count)
            _batch_records.add(row_count, {"batch.id": str(batch_id)})

            # Quality gate ─────────────────────────────────────────────────
            with instrument_quality_check(
                "null_check", "orders_stream", column="amount"
            ) as qspan:
                if row_count > 0:
                    null_count: int = (
                        batch_df.filter(  # type: ignore[attr-defined]
                            batch_df.amount.isNull()  # type: ignore[attr-defined]
                        ).count()
                    )
                    null_pct = round(null_count / row_count * 100, 2)
                else:
                    null_pct = 0.0
                status = "PASS" if null_pct <= max_null_pct else "FAIL"
                qspan.set_attribute("quality.check.null_pct", null_pct)
                qspan.set_attribute("quality.check.status", status)

            # Write to sink ─────────────────────────────────────────────────
            (
                batch_df.write.mode("append").parquet(  # type: ignore[attr-defined]
                    "/tmp/dataobs-streaming-output"
                )
            )

            elapsed_ms = int((time.monotonic() - t0) * 1000)
            span.set_attribute("spark.streaming.batch.duration_ms", elapsed_ms)
            _batch_duration.record(elapsed_ms, {"batch.id": str(batch_id)})

    return _process_batch


def run_streaming(spark: object, await_termination: bool = True) -> object:
    """
    Build and start a Structured Streaming query.

    Args:
        spark:              Active ``SparkSession``.
        await_termination:  Block until the query stops (``False`` for tests).

    Returns:
        The active ``StreamingQuery`` (useful in tests).
    """
    from pyspark.sql import functions as F, types as T  # type: ignore[import]

    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("KAFKA_TOPIC", "orders")

    schema = (
        T.StructType()
        .add("order_id", T.LongType())
        .add("customer_id", T.LongType())
        .add("amount", T.DoubleType())
        .add("event_time", T.TimestampType())
    )

    raw_stream = (
        spark.readStream.format("kafka")  # type: ignore[attr-defined]
        .option("kafka.bootstrap.servers", bootstrap)
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .load()
        .select(
            F.from_json(F.col("value").cast("string"), schema).alias("data")
        )
        .select("data.*")
    )

    query = (
        raw_stream.writeStream.foreachBatch(_make_batch_processor())
        .option("checkpointLocation", "/tmp/dataobs-streaming-checkpoint")
        .trigger(processingTime="30 seconds")
        .start()
    )

    if await_termination:
        query.awaitTermination()  # type: ignore[attr-defined]
    return query


def main() -> None:
    from pyspark.sql import SparkSession  # type: ignore[import]

    setup_spark_otel_provider(
        app_id=os.getenv("SPARK_APP_ID", "dataobs-streaming-example"),
    )

    spark = (
        SparkSession.builder.appName("dataobs-streaming-example")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )

    sc = spark.sparkContext
    sc._jvm.SparkContext.getOrCreate().addSparkListener(  # type: ignore[attr-defined]
        OTelSparkListener()
    )

    try:
        run_streaming(spark)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
