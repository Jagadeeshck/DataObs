# AWS data platform collector

## Status and architecture

AWS collector v1 is **functional_unvalidated**. It is an Integration SDK v1 provider, not a second framework. Explicit
registration creates a provider per bounded execution. A private client factory uses the boto3 credential chain,
optionally calls STS AssumeRole, and caches clients only for that execution by account, region and service. Collection
loops isolate every region and service; stable, redacted partial failures do not discard other metadata.

The v1 services are RDS/Aurora instances and clusters, Glue jobs/crawlers/workflows/triggers and bounded runs, Athena
workgroups and bounded query history, EMR Serverless applications and bounded runs, and static CloudWatch metrics.
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

Static bounds cover 20 regions, four services, 100 API pages, 50 recent runs per request, 100 CloudWatch queries,
1,000 datapoints, 10,000 observations and SDK/runtime deadlines. Exact-commit hosted evidence remains pending.
