# Stream capacity and saturation runtime v1

The capacity stage reuses Stream Intelligence leases, fencing, immutable evidence, OCC projections, checkpoints,
`PartitionSkew`, and `RetentionForecast`. Capacity dimensions remain independent. A missing limit means unknown
headroom; throughput and backlog are demand/pressure evidence, not capacity. Only throttling, authoritative quota or
limit exhaustion, and capacity rejection establish saturation. Hot partitions and queues are bottleneck candidates,
never root-cause claims.

Provider normalization preserves Kafka offset lag, Kinesis stream mode and shard evidence, SQS approximate backlog
and age (never consumer lag), RabbitMQ queue pressure, Pub/Sub subscription backlog, Event Hubs checkpoints, Service
Bus entity counts, and Pulsar partition evidence. Percentages are emitted only with compatible known limits.
