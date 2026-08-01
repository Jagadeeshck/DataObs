# AWS data platform collector

## Status and architecture

AWS collector v2 is **functional_unvalidated**. It extends the same Integration SDK provider rather than creating a second framework. Explicit
registration creates a provider per bounded execution. A private client factory uses the boto3 credential chain,
optionally calls STS AssumeRole, and caches clients only for that execution by account, region and service. Collection
loops isolate every region and service; stable, redacted partial failures do not discard other metadata.

The v1-compatible services are RDS/Aurora instances and clusters, Glue jobs/crawlers/workflows/triggers and bounded runs, Athena
workgroups and bounded query history, EMR Serverless applications and bounded runs, and static CloudWatch metrics.
V2 adds S3 bucket inventory and configured-prefix samples, Lambda functions, SageMaker infrastructure and bounded job
history, MWAA managed environments, Redshift clusters, and Redshift Serverless namespaces/workgroups. The stable service
registry is `rds`, `glue`, `athena`, `emr-serverless`, `s3`, `lambda`, `sagemaker`, `mwaa`, `redshift`, and
`redshift-serverless`; boto3 names are explicitly mapped.
Capabilities are resource discovery, metadata, metrics, health and incremental collection. Logs, SQL, profiling,
lineage, cost, event-driven collection, remediation and complete account coverage are not claimed.

## Evidence, checkpoints, and safety

Canonical SDK IDs deduplicate overlap/replay. Append-only observation evidence and current checkpoint/run state are
tenant/environment scoped. Elasticsearch bulk writes are capped at 250 and checkpoints advance only after required
persistence succeeds. Mutable histories use a default 15-minute overlap; metrics overlap by one period. Account,
region, service and capability never share one cursor. Measured zero is evidence; missing uses `value=null` and cannot
imply health.

Metadata is allowlisted. SQL, endpoints, job arguments/drivers, scripts, connection/result locations, credentials,
external IDs, raw errors and logs are excluded. Tags are bounded, secret-like keys removed, and ownership is unknown
unless a configured key exists. Telemetry uses only provider/service/bounded region category/capability/status/error
code labels; customer identifiers and payloads are prohibited.

S3 never calls `GetObject`: only explicitly configured prefixes are sampled, with count/bytes/latest timestamp and an
honest truncation state. Lambda environment variables and code, SageMaker data/model/notebook content, MWAA Airflow
DAG/run/task data, Redshift endpoints/users/SQL, and raw errors are excluded. Team 2 owns future Airflow normalisation;
the MWAA environment canonical identity is its hand-off contract.

History cursor scopes include tenant, environment, integration, account, region, service, history type, and capability.
Training, processing, transform, pipeline execution, S3 prefix, Redshift summary and metric windows are independent.
Persistence precedes checkpoint advancement and failure of one scope cannot advance it or block unrelated scopes.

Static bounds cover 20 regions, ten services, 100 API pages, 50 recent runs per request, 100 CloudWatch queries,
1,000 datapoints, 10,000 observations and SDK/runtime deadlines. Exact-commit hosted evidence remains pending.
