# Kafka collection failures

Use `python -m services.kafka_observer.cli status --config <path>` first. Readiness is false for Elasticsearch or required Kafka failure; optional provider absence is reported as `not_configured`.

Authentication and permission failures require correcting the referenced secret or broker ACL. Source failures retain prior good projections and advance failure/backoff checkpoint metadata. Lease contention normally means another healthy replica owns that capability. Persistent contention after the lease expiry warrants checking clock synchronization and Elasticsearch availability. Bounded exponential backoff prevents a tight retry loop.

