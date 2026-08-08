# Azure Data Platform Collector v1 audit

## Repository baseline

- Audited base: `ee8bb0363df503e60c85136f6d46ecb6ce606633`.
- Dynamic terminal migration at audit time: `0026_stream_anomaly_retention_intelligence`.
- Registry before this change: `aws`, `snowflake`, `databricks`, `bigquery`; v1 adds explicit `azure` registration.
- `0022_aws_data_platform_collector` introduced generic tenant-scoped provider checkpoints, provider observations, and collection-run streams. Their provider discriminator and safe source-evidence object support Azure, so no migration was added and no released migration was edited.

## Search and ownership classification

`packages/streaming/adapters/azure_messaging.py` and Azure contracts in `packages/streaming/contracts.py` are reusable provider-neutral **Team 1-owned production messaging code**, but are deliberately untouched: Event Hubs and Service Bus are outside this collector. Team 2 job/run reliability, Spark integrations, API job routes, and lineage projections are **Team 2-owned production code** and are not imported. Existing AWS, Snowflake, Databricks, and BigQuery providers and the Integration SDK are reusable Team 4 production patterns. Fake clients under tests are test utilities; `src/poc/spark_*` is POC/demo code. No obsolete Team 4 Azure data-platform provider was found.

## Design decision

Azure Public Cloud only; explicit subscription and named ADF factories, Synapse workspaces, and ADLS accounts prevent tenant-wide discovery. Deterministic non-interactive modes are managed identity, workload identity, and referenced service-principal secret. There is no `DefaultAzureCredential`, CLI, PowerShell, browser, device-code, username/password, inline token, or arbitrary authority/endpoint path.

Supported SDK ranges are Azure Identity `>=1.19,<2`, Resource `>=23,<24`, Data Factory `>=9,<10`, Synapse `>=2,<3`, Storage management `>=22,<24`, Data Lake `>=12.17,<13`, and Azure Core `>=1.32,<2`. SDK-selected stable clients determine REST API versions; the provider does not issue arbitrary REST calls.

Supported source evidence comprises ADF factory/pipeline/trigger/pipeline-run/activity-run, Synapse workspace/SQL-pool/Spark-pool/pipeline/pipeline-run/activity-run, and ADLS account/filesystem/aggregate prefix observations. Supported capabilities are discovery, metadata, metrics, health, and incremental collection. Logs, query history, lineage, cost, event-driven collection, canonical jobs, SQL query observability, Spark execution observability, data quality, and whole-subscription coverage are unsupported.

Security risks are over-broad RBAC, sensitive pipeline payloads, file-content access, unbounded history, credential fallback, and path disclosure. Controls are field allowlists, operation allowlists, strict identifiers, referenced credentials, fixed endpoints, bounded windows/pages/results, aggregate-only prefix output, redacted stable errors, and generic tenant/environment/integration persistence boundaries.

Cross-team dependencies: Team 0 owns packaging and shared release/security controls; Team 2 may later project the documented safe source fields; Team 5 owns onboarding UI. Status remains `functional_unvalidated` until hosted exact-commit evidence is retained and independently verified.
