# Stream and pathway reliability product

The single canonical evaluator is `packages/streaming/reliability.py`. Bounded stream/pathway projections are converted to observations, evaluated against due tenant/environment definitions, appended to the appropriate evaluation data stream, projected to current status, and optionally emitted as redaction-safe Team 1 reliability signals. Persistence precedes checkpoint advancement.

Supported resources are Kafka clusters, topics, consumer groups, connectors, and pathways. The capability registry is authoritative for their metrics. Missing is never coerced to zero; measured zero remains a value. Stale and error evidence cannot produce healthy. Pathway latency records distinguish `trace_derived`, `edge_estimate`, and `unavailable`; correlation is not causation.

Definitions use `gt`, `gte`, `lt`, or `lte`, bounded windows/intervals, positive breach/recovery counts, and `no_data`, `breach`, or `ignore` missing policies. Drafts are disabled. Transitions are warning, breaching, recovering, healthy, no_data, stale, error, and disabled. Renewable leases and monotonically increasing fencing tokens reject stale writers. Deterministic evaluation and signal identifiers make retries idempotent.

Pathway SLO CRUD remains backward compatible; reliability status/history are additive. This product does not remediate resources or write Team 3 private incident indices.
