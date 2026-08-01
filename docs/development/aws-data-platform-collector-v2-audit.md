# AWS data platform collector v2 audit

Audited base: `232a8e073cbfedf0d0c2444e9be23b59e959a4ee` (including merged PR #197 at `503435b`). PR #197 established the
Integration SDK provider, per-execution client factory, RDS/Glue/Athena/EMR Serverless collectors, static CloudWatch
adapter, tag/ownership filtering, redacted failures, repositories, and migration 0022.

Repository searches found production AWS code in `integrations/aws`, runtime persistence in
`services/collection_manager`, and SDK contracts in `packages/collectors/sdk`. `integrations/aws-lambda` is an older
deployment/telemetry integration and was rejected as POC/packaging-adjacent rather than reused. Airflow and Spark code
belongs to Team 2 and is not imported. Fixture POCs and Grafana AWS examples are not collector implementations.

V2 reuses provider registration, observations, canonical IDs, tagging, ownership, error mapping, client isolation,
durable checkpoints, run repository, and migration 0022. Its generic provider-observation evidence contract stores
bounded `source_evidence`; no strict service-specific field mapping is required, so no 0023 migration was added and
released migrations were not edited.

Exact scope is the four v1 services plus S3 buckets/configured prefixes, Lambda metadata, SageMaker operational
inventory/bounded histories, MWAA environment metadata, and provisioned/serverless Redshift inventory. CloudWatch is
allowlisted. Query summaries are optional and SQL-free; where the safe Data API is unavailable they remain unsupported
rather than opening database connections.

Compatibility risks are service API/version differences, optional permissions, delayed/dimensioned metrics, global S3
bucket listing, and history pagination. Bounds, explicit regions/prefixes, missing evidence, and isolated failures
mitigate these. Team 0 must package boto3/runtime changes and independently verify hosted evidence. Team 2 owns Airflow
DAG/run/task normalisation. Team 5 owns onboarding UI; the YAML/CLI remains the supported configuration path.
