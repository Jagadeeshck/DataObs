# DataObs — Spark Instrumentation (PySpark + OTel SDK)

OTel-based instrumentation for PySpark jobs. Emits job, stage, and task
lifecycle **spans**, **metrics**, and **logs** following OTel semantic
conventions.

## Directory Layout

```
integrations/spark/
├── README.md                      # This file
├── otel_spark.py                  # SparkListener → OTel bridge (shared helpers)
├── example_etl_job.py             # Fully instrumented batch ETL example
├── example_streaming.py           # Structured Streaming with OTel
├── requirements.txt
└── config/
    └── otel-collector-spark.yaml  # Dedicated OTel Collector pipeline
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r integrations/spark/requirements.txt
```

### 2. Start the OTel Collector

```bash
ES_ENDPOINT=http://localhost:9200 \
GRAFANA_TEMPO_ENDPOINT=http://localhost:4317 \
docker run --rm \
  -v $(pwd)/integrations/spark/config:/conf \
  -p 4317:4317 -p 4318:4318 -p 8889:8889 \
  otel/opentelemetry-collector-contrib:0.102.0 \
  --config /conf/otel-collector-spark.yaml
```

### 3. Run the ETL example

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
OTEL_SERVICE_NAME=my-spark-job \
spark-submit integrations/spark/example_etl_job.py
```

### 4. Run the Streaming example

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
OTEL_SERVICE_NAME=my-spark-streaming \
KAFKA_BOOTSTRAP_SERVERS=broker:9092 \
KAFKA_TOPIC=orders \
spark-submit integrations/spark/example_streaming.py
```

## Key Files

| File | Purpose |
|------|---------|
| `otel_spark.py` | SparkListener → OTel bridge, shared SDK setup, DataFrame/QC helpers |
| `example_etl_job.py` | Fully instrumented batch ETL with quality-gate spans |
| `example_streaming.py` | Per-micro-batch spans + quality checks |
| `config/otel-collector-spark.yaml` | Collector pipelines (traces → Tempo, metrics → Prometheus, logs → ES) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_SERVICE_NAME` | `spark-job` | `service.name` resource attribute |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTel Collector gRPC endpoint |
| `OTEL_SDK_DISABLED` | `false` | Set `true` to disable SDK (useful in tests) |
| `DEPLOY_ENV` | `development` | `deployment.environment.name` |
| `SPARK_APP_ID` | `spark-app` | `spark.app.id` resource attribute |
| `SPARK_MASTER` | `local[*]` | `spark.master` resource attribute |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Streaming example only |
| `KAFKA_TOPIC` | `orders` | Streaming example only |

## OTel Semconv Attributes

### Spans

| Attribute | Example | Semconv |
|-----------|---------|---------|
| `db.system` | `spark` | [db](https://opentelemetry.io/docs/specs/semconv/database/) |
| `spark.job.id` | `42` | custom |
| `spark.job.result` | `JobSucceeded` | custom |
| `spark.stage.id` | `7` | custom |
| `spark.stage.attempt` | `0` | custom |
| `spark.stage.num_tasks` | `200` | custom |
| `quality.check.name` | `null_check` | custom |
| `quality.check.status` | `PASS` | custom |

### Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| `spark.job.duration` | ms | Wall-clock duration per job |
| `spark.stage.shuffle.bytes` | By | Shuffle bytes written per stage |
| `spark.stage.spill.bytes` | By | Disk bytes spilled per stage |
| `spark.stage.gc.time` | ms | JVM GC time per stage |
| `spark.executor.memory.used` | By | Executor JVM heap used |
| `spark.records.processed` | {records} | Total records read/written |
| `spark.streaming.batch.duration` | ms | Micro-batch wall-clock time |
| `spark.streaming.batch.lag` | ms | Approximate consumer lag |

## Using `otel_spark` in Your Own Job

```python
from otel_spark import (
    setup_spark_otel_provider,
    OTelSparkListener,
    instrument_dataframe,
    instrument_quality_check,
    record_executor_memory,
)

# 1. Bootstrap SDK (call once at driver startup)
setup_spark_otel_provider(app_id="my-job")

# 2. Register listener on driver SparkContext
sc._jvm.SparkContext.getOrCreate().addSparkListener(OTelSparkListener())

# 3. Wrap DataFrame operations
df = instrument_dataframe(df, "read", "orders")

# 4. Wrap quality checks
with instrument_quality_check("null_check", "orders", column="email") as span:
    result = null_check.run(config, engine)
    span.set_attribute("quality.check.status", result.status)

# 5. Emit executor memory gauge (call from executor metric listener)
record_executor_memory(executor_id="1", used_bytes=512 * 1024 * 1024)
```

## Grafana Dashboard Import

1. Open Grafana → **Dashboards** → **Import**.
2. Paste the JSON from `docs/grafana/spark-otel-dashboard.json` (if present).
3. Select your Prometheus and Tempo data sources.

Spans appear under **Explore → Tempo** with service name matching
`OTEL_SERVICE_NAME`. Metrics appear in the `spark_*` namespace in Prometheus.

Resolves: [#27](https://github.com/Jagadeeshck/DataObs/issues/27)


## Job Explorer boundary

OpenLineage supplies application/dataset lineage. Replayable Spark event logs supply bounded stage/task/executor and Structured Streaming operational evidence; offsets are represented only by redacted hashes.
