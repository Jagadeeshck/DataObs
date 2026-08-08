# Collection Manager

Minimal tenant-aware control plane for source, integration, collector, scanner, heartbeat, scan-policy, scanner-task, and synthetic scanner-result workflows. Fleet and EDOT adapters are explicit `not_implemented` boundaries.

## BigQuery provider

The explicit registry includes BigQuery warehouse collector v1. Its official Google dependencies are optional and lazy; configuration requires explicit projects/locations. See `docs/integrations/bigquery.md`.

Azure data platform collector v1 is also registered explicitly. Azure SDK dependencies are optional and lazy, and only configured ADF factories, Synapse workspaces, and ADLS Gen2 accounts are accessed. See `docs/architecture/azure-data-platform-collector.md`.
# Provider composition

The explicit provider composition includes AWS, Snowflake, Databricks, BigQuery, Azure, Trino, and Presto. Their distinct official clients remain optional lazy dependencies; validation uses the closed parser map and does not dynamically load Python paths.
