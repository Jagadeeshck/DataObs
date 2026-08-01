# Databricks Lakehouse Collector v1 audit

The audited base is `043a4e368d40f0fe04d8d48610b1af613985357b`. The executable registry, queried with
`python scripts/release/current_terminal_migration.py`, terminates at `0024_job_run_reliability_runtime`; release metadata
was stale before this change. Migration `0022_aws_data_platform_collector` already supplies strict, generic tenant-scoped
provider observation, run, and checkpoint storage, so no migration is justified or added.

The explicit registry contained `aws` and `snowflake`; v1 adds `databricks`. Reused production components are the SDK
contracts, retry/runtime, secret-reference pattern, canonical IDs, generic persistence, OCC checkpoints, and Snowflake's
allowlist/partial-family approach. Existing `integrations/spark` is instrumentation/demo and its normalizer, along with
`services/job_reliability` and `packages/domain_model/job_run.py`, is Team 2-owned canonical projection and is deliberately
not reused. No production Databricks collector was found.

The optional official dependency is `databricks-sdk>=0.60,<1`, lazy imported. OAuth M2M is primary; opt-in legacy PAT
requires an environment reference; workload identity is deferred because deterministic, profile-free tenant isolation is
not established here. Workspace APIs use the SDK, Unity Catalog REST inventory, SQL Warehouses APIs, Jobs API 2.2
semantics, and fixed Statement Execution queries. Supported evidence is workspace, catalogs, schemas, tables/views,
columns, volumes, warehouses/health, job definitions/runs, optional preview query history, and warehouse events. Files,
rows, SQL text, identities, lineage, Spark normalization, costs, mutations, and account-console administration are deferred.
