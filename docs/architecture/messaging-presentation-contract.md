# Messaging presentation contract

The `src/messaging` package adapts Team 1 contracts for display. Its provider registry stores names, textual marks, and labels only. Capability state comes exclusively from `GET /api/v1/streams/providers`.

Canonical identity is the server's provider, messaging system, resource kind, and canonical resource ID. Labels never form identity. Metric evidence distinguishes measured, estimated, inferred, forecast, missing, stale, partial, unavailable, and unsupported. Queue depth, consumer lag, age, and retention are not interchangeable.
