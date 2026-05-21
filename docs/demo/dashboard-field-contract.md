# Dashboard Field Contract (Road Safety POC)

All dashboard-backed indices now use normalized fields where applicable:
`@timestamp`, `run_id`, `run_mode`, `scenario`, `dataset`, `asset_id`, `asset_name`, `status`, `severity`, `check_name`, `check_type`, `message`, `records_processed`, `input_rows`, `output_rows`, `rejected_rows`, `failed_checks`, `stage_name`, `stage_duration_seconds`, `source_dataset`, `target_dataset`, `relation_type`.

## Index contracts
- `dataobs-quality`: quality check events with `check.*`, `asset.*`, normalized check aliases (`check_name`, `check_type`, `status`, `severity`, `message`), plus `run_id`.
- `dataobs-alerts`: alert events with `alert.*`, `asset.*`, `severity`, `status`, `run_id` when available.
- `dataobs-freshness`: freshness lag + status per dataset/asset.
- `dataobs-volume`: volume anomaly status and row count bands.
- `dataobs-schema`: schema snapshots and drift status/events.
- `dataobs-lineage`: source/target lineage using `lineage.source`, `lineage.target`, and aliases `source_dataset`, `target_dataset`, `relation_type`.
- `dataobs-assets`: asset catalog records.
- `dataobs-spark-metrics`: stage-level metrics (`stage_name`, `stage_duration_seconds`, `input_rows`, `output_rows`, `rejected_rows`, `failed_checks`).
- `dataobs-rs-*`: scenario outputs include `run_id`, `run_mode`, `scenario=road_safety`, and `@timestamp`.

## First-look dashboard expectations
- Executive: KPI tiles for run health, alerts, processed rows, failed checks; plus severity and dataset breakdowns.
- Quality: status distribution, check-type failures, dataset failures, and failure detail tables.
- Freshness/Volume/Schema: stale datasets KPI, freshness table/bar, row-count trend, anomaly and drift tables.
- Lineage: source→target lineage and downstream impact summaries.
- Spark: stage durations, row flow, rejects, slowest/failed stages.
