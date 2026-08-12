# Operating the Team 4 MySQL collector

Start with `config/integrations/mysql-database.example.yaml`, which is disabled. Use a dedicated restricted principal, set the referenced secret, mount a trusted CA, validate configuration, and test connectivity before collection. TLS certificate and hostname verification are mandatory. The connector disables local infile; multi-statements, arbitrary flags, init commands, plugin directories, arbitrary session variables, DSNs, and arbitrary SQL are not configurable.

Metadata collection is independent by schemas, relations, columns, constraints, indexes, and partitions. A denied family emits a stable redacted partial failure and preserves successful siblings. `result_truncated` means the corresponding configured limit must be reviewed. Dynamic table statistics are disabled by default and the collector never runs `ANALYZE TABLE`.

Freshness and profiling are disabled by default. Freshness permits only an explicitly configured `MAX(timestamp_column)`. Profiling permits bounded provider-generated aggregates (count, null/distinct count, min/max, and length bounds), never samples, top values, predicates, histograms, or free SQL. Persistence through generic provider storage must succeed before its generic OCC checkpoint advances; failed scopes do not advance.
