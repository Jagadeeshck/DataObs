"""
DataObs POC Pipeline Package
============================

Provides a config-driven, end-to-end local data pipeline that:

1. Discovers and downloads public open datasets (default: data.gov.uk / CKAN)
2. Processes them with local PySpark
3. Runs baseline data-quality checks (freshness, nulls, row count, duplicates)
4. Indexes raw, curated, quality, and lineage documents into Elasticsearch
5. Emits structured telemetry (traces/metrics/logs) via OpenTelemetry
6. Bootstraps Kibana saved objects (index patterns + dashboards)

Enable by setting ``poc.enabled: true`` in ``config/dataobs.yaml``.
If ``poc.data_sources`` is empty the pipeline auto-discovers datasets from
data.gov.uk via the CKAN API.

Entrypoints
-----------
  python -m src.poc.spark_job           # run pipeline
  python -m src.poc.bootstrap_kibana    # load Kibana saved objects
  scripts/run_poc_pipeline.sh           # both in sequence
"""
