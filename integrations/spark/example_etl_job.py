"""
Fully instrumented PySpark ETL job example.

Usage::

    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
    OTEL_SERVICE_NAME=spark-etl-orders \
    spark-submit integrations/spark/example_etl_job.py

Resolves: https://github.com/Jagadeeshck/DataObs/issues/27
"""
from __future__ import annotations

import os

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

from otel_spark import OTelSparkListener, instrument_dataframe

# Bootstrap OTel SDK
resource = Resource.create(
    {
        SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "spark-etl"),
        "spark.app.id": "example-etl",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    }
)
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("spark.etl.example")


def main() -> None:
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName("dataobs-etl-example").getOrCreate()
    sc = spark.sparkContext
    sc._jvm.SparkContext.getOrCreate().addSparkListener(OTelSparkListener())  # type: ignore[attr-defined]

    with tracer.start_as_current_span("etl.pipeline", attributes={"etl.table": "orders"}):
        df = spark.range(10_000).toDF("id")
        df = instrument_dataframe(df, "read", "orders")

        with tracer.start_as_current_span("etl.transform"):
            result = df.filter("id % 2 == 0")

        with tracer.start_as_current_span("etl.write"):
            result.write.mode("overwrite").parquet("/tmp/dataobs-etl-output")

    spark.stop()


if __name__ == "__main__":
    main()
