# Collection Manager

Minimal tenant-aware control plane for source, integration, collector, scanner, heartbeat, scan-policy, scanner-task, and synthetic scanner-result workflows. Fleet and EDOT adapters are explicit `not_implemented` boundaries.

## BigQuery provider

The explicit registry includes BigQuery warehouse collector v1. Its official Google dependencies are optional and lazy; configuration requires explicit projects/locations. See `docs/integrations/bigquery.md`.

Azure data platform collector v1 is also registered explicitly. Azure SDK dependencies are optional and lazy, and only configured ADF factories, Synapse workspaces, and ADLS Gen2 accounts are accessed. See `docs/architecture/azure-data-platform-collector.md`.
# Provider composition

The explicit provider composition includes AWS, Snowflake, Databricks, BigQuery, Azure, Trino, and Presto. Their distinct official clients remain optional lazy dependencies; validation uses the closed parser map and does not dynamically load Python paths.

MySQL provider type `mysql`, version `1`, is explicitly registered alongside PostgreSQL and the existing cloud/SQL-engine providers. Install `requirements-mysql.txt` only on MySQL workers; missing Connector/Python fails as `dependency_unavailable`. Generic provider observations and persist-before-advance OCC checkpoints are reused.

MariaDB provider type `mariadb`, version `1`, is explicitly registered separately from MySQL. Its generic observations use the existing persist-before-advance OCC checkpoint path; install `requirements-mariadb.txt` only on MariaDB workers.

Microsoft SQL Server provider type `sqlserver`, version `1`, uses the same generic observation and persist-before-advance OCC checkpoint path. Install optional `requirements-sqlserver.txt` only on SQL Server workers.

## Oracle database provider v1

The registry includes `oracle` v1 using python-oracledb Thin mode. It requires structured TCPS service/PDB configuration and exposes accessible structural metadata, policy-owned freshness, and aggregate-only profiling. Query history, AWR/ASH, SQL text, and raw-row persistence are unsupported. See `config/integrations/oracle-database.example.yaml`.
