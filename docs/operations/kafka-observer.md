# Operating the Kafka observer

Configure `tenant_id`, `environment`, `integration_id`, broker endpoints, and secret references in the observer YAML. Production uses TLS and credentials referenced through `env:` or `file:`; resolved values are never printed.

Default intervals are inventory 300s, groups/offsets/metrics 30s, Connect 60s, and schemas 300s. Increase intervals or reduce configured bounds for large estates. Replica scaling is safe because capability leases are scoped by tenant, environment, and integration. After restart, durable checkpoints retain cursors, fingerprints, attempts, successes, failures, and retry state.

Connect and Schema Registry are optional. Their URL and host allowlist must be configured together. Offset collection considers only assigned partitions, is capped per cycle, and preserves unknown commits and watermarks as null rather than zero.

