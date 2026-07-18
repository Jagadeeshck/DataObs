# Elasticsearch storage and migrations

```mermaid
flowchart TB
  api[Product APIs] --> mutable[Versioned mutable state indices]
  scanner[Scanner results] --> streams[Append-only data streams]
  streams --> latest[Transforms/latest-state projections]
  mutable --> kibana[Kibana analytics and alerting]
```

Migration `0001_product_foundation` creates state index `dataobs-system-migrations-v1`, product state indices, read/write aliases, data-stream templates, and latest-state transform definitions. Production readiness fails until required migrations are applied.
