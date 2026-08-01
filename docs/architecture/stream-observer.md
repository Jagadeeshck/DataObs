# Kafka Stream Observer

The one Kafka observer composes Kafka Admin inventory, consumer group assignments, assigned-partition offsets and watermarks, optional Kafka Connect, optional Schema Registry, and optional metrics. Capability bindings select exactly one authority; conflicting authorities fail closed unless comparison mode is explicit.

Each capability has an independent due time and lease. A bounded thread pool prevents a slow HTTP or broker call from permanently blocking other capabilities. Elasticsearch resources installed by migrations 0009 and 0010 hold append-only evidence, current projections, scoped checkpoints, and renewable leases. Expiry transfers ownership with a monotonically increasing fencing token.

Lag is `max(high_watermark - committed_offset, 0)` only when both inputs exist. Velocity needs two observations. Drain time is finite only when processing exceeds input. Delete-retention risk is `safe`, `warning`, `at_risk`, or `data_loss_suspected`; compact-only topics are `not_applicable`.

