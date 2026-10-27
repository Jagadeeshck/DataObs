# Team 4 Google Pub/Sub messaging collector

The `gcp` v1 provider is a read-only Collection Manager plugin for explicitly configured Google Cloud projects and
the `pubsub` service only. It lists topics and subscriptions through official admin clients and emits bounded generic
provider observations whose safe envelopes are accepted by Team 1's `PubSubAdapter`. BigQuery remains the independent
`bigquery` provider.

The collector stores structural inventory, declared retention/exactly-once/ordering configuration, privacy-safe
delivery categories, filter fingerprints, and visible dead-letter topology. KMS names, schema bodies, transforms,
push destinations, export destinations, OIDC identities, raw filters, messages, attributes and acknowledgement IDs
are never retained. The read-only client boundary does not expose publish, pull, acknowledge, seek, snapshot, or
mutation methods.

Cloud Monitoring uses a fixed GA metric allowlist. Regional subscription backlog metrics are preferred; global
metrics are explicit fallback evidence. Missing points remain missing, measured zero remains zero, GAUGE values remain
points, and DELTA values retain their alignment window rather than becoming lifetime counters. Team 1 still owns all
canonical projections and does not yet project every metric/backlog/retention/DLQ family.
