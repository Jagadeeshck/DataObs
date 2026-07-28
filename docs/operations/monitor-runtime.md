# Monitor runtime operations

Configure `ELASTICSEARCH_URL`, credentials or API key, `DATAOBS_TENANT_ID`, `DATAOBS_ENVIRONMENT`, and a secret-injected
`DATAOBS_MONITOR_POSTGRES_DSN`. `DATAOBS_MONITOR_POSTGRES_ALLOWLIST` maps `schema.table` to permitted columns. Production
TLS defaults to `require`; set `DATAOBS_MONITOR_POSTGRES_SSLMODE` only under an approved connection policy.

Use `python -m services.monitor_runtime.cli health` for readiness and `once` for a bounded operational canary. Exit code 2
means composition or readiness failed. Do not restart-loop past missing migrations or provider configuration. Backlog is
the bounded due batch, not an unbounded cardinality query. Stop the deployment to halt claims; append-only evidence and
additive Elasticsearch resources remain intact. On rollback, archive or disable definitions created during rollout rather
than deleting evidence.
