# Data Observability MVP

This feature adds a Datadog-inspired data observability foundation using Elasticsearch-friendly documents and FastAPI endpoints. It covers catalog assets, column metadata, quality checks/runs, job runs, OpenLineage-like ingestion, lineage edges, and basic asset health.

## Elasticsearch indices

Composable templates are defined in `src/data_observability/mappings.py` for:

- `dataobs-assets-v1`: asset ids, names, ownership, tags, timestamps, health.
- `dataobs-columns-v1`: asset columns/fields, data types, nullable/PII flags, samples and stats.
- `dataobs-quality-checks-v1`: quality rule definitions and thresholds.
- `dataobs-quality-runs-v1`: check execution results, values, severity and timing.
- `dataobs-job-runs-v1`: Airflow/dbt/Spark/Glue/Databricks/custom run metadata.
- `dataobs-lineage-edges-v1`: source-to-target dependency edges.
- `dataobs-incidents-v1`: reserved for future incident workflow.

IDs, owners, statuses, types, source systems, domains and tags use keyword mappings. Names and descriptions use text plus keyword multi-fields. Timestamps are dates; metric values and durations are numeric.

## APIs

Run locally with memory storage:

```bash
DATAOBS_STORE_BACKEND=memory DATAOBS_ALLOW_UNAUTHENTICATED_DEV=true uvicorn src.api.app:create_app --factory --reload
```

Examples:

```bash
curl -X POST http://localhost:8080/api/data-observability/assets -H 'Content-Type: application/json' -d '{"asset_id":"warehouse:analytics.orders","name":"orders","asset_type":"table","source_system":"warehouse","owner":"data-platform","domain":"commerce","criticality":"critical","tags":["orders"],"description":"Order facts"}'
curl 'http://localhost:8080/api/data-observability/assets?q=orders'
curl -X POST http://localhost:8080/api/data-observability/quality-runs -H 'Content-Type: application/json' -d '{"check_id":"qc_orders_freshness","asset_id":"warehouse:analytics.orders","status":"pass","observed_value":1,"expected_value":3,"severity":"critical","message":"fresh","duration_ms":1000}'
curl -X POST http://localhost:8080/api/data-observability/job-runs -H 'Content-Type: application/json' -d '{"job_name":"build_orders","job_type":"dbt","source_system":"dbt","status":"success","started_at":"2026-07-08T00:00:00Z","finished_at":"2026-07-08T00:05:00Z","duration_ms":300000,"input_assets":["warehouse:raw.orders"],"output_assets":["warehouse:analytics.orders"],"error_message":""}'
curl -X POST http://localhost:8080/api/data-observability/lineage/events -H 'Content-Type: application/json' --data @examples/data_observability/openlineage_event.json
curl 'http://localhost:8080/api/data-observability/assets/warehouse:analytics.orders/lineage'
curl 'http://localhost:8080/api/data-observability/assets/warehouse:analytics.orders/health'
```

## OpenLineage-compatible subset

Supported payload fields are `eventType`, `eventTime`, `run.runId`, `job.name`, `inputs[]`, and `outputs[]`. Each dataset should include `namespace` and `name`. The service converts inputs/outputs into asset IDs as `{namespace}:{name}`, records a job run, and creates lineage edges from every input to every output.

## Sample data

See `examples/data_observability/sample_data.json` and `examples/data_observability/openlineage_event.json`.

## Limitations and next steps

This iteration intentionally provides mock/framework execution only. Real Snowflake, BigQuery, Databricks, Redshift, Glue, dbt, Airflow, Spark, Kafka, SQS and Kinesis connectors can be added behind the service layer. Health is rule-based and should later be time-windowed with freshness SLAs and incident correlation.
