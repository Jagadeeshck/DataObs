"""
Fully instrumented PySpark ETL job example.

Demonstrates:
  - SDK bootstrap via ``setup_spark_otel_provider``
  - Job/stage lifecycle telemetry via ``OTelSparkListener``
  - DataFrame read/write spans via ``instrument_dataframe``
  - Quality-check spans via ``instrument_quality_check``
  - Data-volume metrics (records processed)

Usage::

    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \\
    OTEL_SERVICE_NAME=spark-etl-orders \\
    spark-submit integrations/spark/example_etl_job.py

Resolves: https://github.com/Jagadeeshck/DataObs/issues/27
"""
from __future__ import annotations

import os
import sys

# Allow running directly without installing as a package.
sys.path.insert(0, os.path.dirname(__file__))

from otel_spark import (
    OTelSparkListener,
    instrument_dataframe,
    instrument_quality_check,
    setup_spark_otel_provider,
)
from opentelemetry import trace


def _null_pct(df: object, column: str) -> float:
    """Return the null percentage for *column* in *df* (PySpark DataFrame)."""
    from pyspark.sql import functions as F  # type: ignore[import]

    total = df.count()  # type: ignore[attr-defined]
    if total == 0:
        return 0.0
    nulls = df.filter(F.col(column).isNull()).count()  # type: ignore[attr-defined]
    return round(nulls / total * 100, 2)


def _run_quality_checks(df: object, max_null_pct: float = 5.0) -> None:
    """Run quality gate checks on *df* and record results as OTel spans."""
    with instrument_quality_check(
        "null_check", "orders", column="customer_id"
    ) as qspan:
        null_pct = _null_pct(df, "customer_id")
        status = "PASS" if null_pct < max_null_pct else "FAIL"
        qspan.set_attribute("quality.check.status", status)
        qspan.set_attribute("quality.check.null_pct", null_pct)


def run_pipeline(spark: object) -> None:
    """Execute the ETL pipeline with full OTel instrumentation."""
    from pyspark.sql import functions as F  # type: ignore[import]

    tracer = trace.get_tracer("spark.etl.example")

    with tracer.start_as_current_span(
        "etl.pipeline",
        attributes={"etl.table": "orders", "etl.version": "1.0"},
    ):
        # ── Read ────────────────────────────────────────────────────────────
        raw_df = spark.range(10_000).toDF("id")  # type: ignore[attr-defined]
        raw_df = raw_df.withColumn("amount", F.rand() * 1000)
        raw_df = raw_df.withColumn(
            "customer_id",
            F.when(F.col("id") % 50 == 0, None).otherwise(F.col("id") % 500),
        )
        raw_df = instrument_dataframe(raw_df, "read", "orders")

        # ── Quality gate ─────────────────────────────────────────────────────
        _run_quality_checks(raw_df)

        # ── Transform ───────────────────────────────────────────────────────
        with tracer.start_as_current_span("etl.transform"):
            result = raw_df.filter("id % 2 == 0").filter("amount > 50")

        # ── Write ───────────────────────────────────────────────────────────
        with tracer.start_as_current_span(
            "etl.write", attributes={"etl.output.format": "parquet"}
        ):
            result = instrument_dataframe(result, "write", "orders_clean")
            result.write.mode("overwrite").parquet("/tmp/dataobs-etl-output")


def main() -> None:
    from pyspark.sql import SparkSession  # type: ignore[import]

    # Bootstrap OTel SDK — must happen before any span/metric creation.
    setup_spark_otel_provider(
        app_id=os.getenv("SPARK_APP_ID", "dataobs-etl-example"),
    )

    spark = (
        SparkSession.builder.appName("dataobs-etl-example")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )

    # Register SparkListener on the driver.
    sc = spark.sparkContext
    sc._jvm.SparkContext.getOrCreate().addSparkListener(  # type: ignore[attr-defined]
        OTelSparkListener()
    )

    try:
        run_pipeline(spark)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

