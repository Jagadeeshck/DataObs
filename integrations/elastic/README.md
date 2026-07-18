# Elastic Integration Reuse Foundation

DataObs reuses packaged Elastic integrations before creating custom collection. Fleet-managed Elastic Agent is the default for supported hosts, Kubernetes, cloud services, databases, brokers, files, APIs, custom logs, custom HTTP API, CEL, SQL query input, Kafka input, and cloud storage/event inputs. DataObs must not manually modify assets managed by an installed Elastic package.

Create a DataObs custom package only when DataObs-specific metadata, quality, schema-diffing, freshness, query-history, scanner health, or OpenLineage correlation is not supplied by an existing integration or OTel receiver. Package names use `dataobs_<domain>` such as `dataobs_database`; datasets use `dataobs.<domain>.<capability>` and tenant namespaces map to Fleet namespaces plus explicit `tenant.id` fields.

ECS is used for Elastic-native events and host/cloud operational telemetry. OTel semantic conventions are preserved for OTLP spans, metrics, and logs. DataObs enrichment adds tenant, environment, integration/source, asset, owner, pipeline, and pillar fields.

## Proposed `dataobs_database` package layout

```text
integrations/elastic/packages/dataobs_database/
  manifest.yml
  data_stream/database_inventory/
  data_stream/schema_snapshot/
  data_stream/schema_change/
  data_stream/freshness/
  data_stream/table_profile/
  data_stream/column_profile/
  data_stream/quality_result/
  data_stream/query_history/
  data_stream/scanner_health/
```

The Elastic SQL input may support simple database custom queries. The DataObs Scanner is required for deeper metadata discovery, stateful diffing, profiling controls, checkpoints, and unsupported platforms. Integration tests must validate package assets, mappings, ingest pipelines, Fleet policy rendering, and upgrade compatibility.
