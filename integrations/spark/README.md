# DataObs — Spark Instrumentation

OTel-based instrumentation for PySpark jobs. Emits job, stage, and task
lifecycle spans + metrics following OTel semantic conventions.

## Quick Start

```bash
pip install -r integrations/spark/requirements.txt

OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
OTEL_SERVICE_NAME=my-spark-job \
spark-submit integrations/spark/example_etl_job.py
```

## Key Files

| File | Purpose |
|------|---------|
| `otel_spark.py` | SparkListener → OTel bridge |
| `example_etl_job.py` | Fully instrumented ETL example |
| `example_streaming.py` | Structured Streaming example |

## Semconv Attributes

| Attribute | Value |
|-----------|-------|
| `db.system` | `spark` |
| `spark.job.id` | Spark job ID |
| `spark.stage.id` | Stage ID |
| `spark.stage.num_tasks` | Tasks in stage |

Resolves: [#27](https://github.com/Jagadeeshck/DataObs/issues/27)
