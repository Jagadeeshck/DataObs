# Pathway worker operations

Use `dataobs-pathway-worker run`, `process-once`, `replay`, or `status` with a
tenant, environment, and source-stream configuration. Each cycle obtains a
durable lease. Its monotonically changing fencing token rejects expired owners
and stale projection/checkpoint writers.

The watermark records the last committed source timestamp and document ID, last
successful processing time, overlap window, worker and fencing identity,
processed count, and consecutive failures. PIT plus deterministic
timestamp/document-ID sorting bounds every cycle. The watermark advances only
after projection persistence succeeds; it never advances to wall-clock time.

Readiness is false when Elasticsearch, migration state, durable lease storage, or
source streams are unavailable. Operators should alert on checkpoint age,
consecutive failures, lease contention, and unavailable source streams.
