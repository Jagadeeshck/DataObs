# AWS data platform collector v1 audit

**Audited base:** `1297937bf66ce0d6b3d869815d1f395df5c27c1e` (2026-08-01).

The Integration SDK and Collection Manager provider runtime were reusable production-oriented foundations. The runtime
nevertheless defaulted to an in-memory checkpoint, returned observations in memory, and had no durable run boundary.
No existing index had both the Team 4 ownership contract and mappings required for account/region/service-scoped
provider checkpoints and redaction-safe provider evidence; migration 0022 is therefore additive. Released migrations
0001--0021 were not edited.

Existing AWS code comprised boto3-based freshness checks and example configuration (legacy POC), the AWS Lambda sample
(example only), Kubernetes CloudWatch receiver configuration (platform-owned), and
`integrations/spark/glue_job_monitor.py`. The latter is Team 2-owned Glue/Spark telemetry and is deliberately unchanged
and not reused: this collector emits only safe source evidence and does not duplicate Spark job/stage normalisation.
The SDK contracts, canonical resource IDs, evidence states, error taxonomy, retry and redaction helpers are reused.

Supported scope is explicit-region discovery for RDS/Aurora, Glue, Athena and EMR Serverless, plus static CloudWatch
metrics. S3, Lambda, SageMaker, MWAA, Redshift, EMR on EC2, Kinesis, DynamoDB, Cost Explorer, CloudTrail, Azure, GCP,
Snowflake and Databricks are future work. Organisation crawling, arbitrary APIs/metrics, SQL/log/data access, profiling,
lineage, incident/remediation behavior, UI onboarding and packaging are unsupported.

Checkpoint identity includes tenant, environment, integration, provider, account, region, service and capability.
Independent scopes are required for inventory, Glue runs, Athena queries, EMR Serverless runs and metrics. Evidence
must persist before advancement. Team 0 must package the runnable service; Team 5 owns onboarding.
