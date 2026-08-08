# Pathway time travel

Migration 0028 introduces strict, tenant/environment/pathway-scoped append-only snapshots retained for 365 days and fenced mutable projector state. A snapshot is written on a semantic node/edge/routing change or a daily safety interval, not on metric changes.

The SHA-256 graph hash covers sorted node ID/type and edge ID/source/destination/type/topic/consumer-group identity. It excludes timestamps, health, lag, latency, throughput and confidence. Nested details are capped at 500 nodes and 1,000 edges.

Time travel selects the latest snapshot whose `effective_at` is at or before T. It never substitutes current topology. Before first collection it returns `history_unavailable`; known inactive, not-yet-observed, truncated, stale and partial states remain distinct. Ordinary evidence queries are limited to 90 days; snapshot availability follows retained history.
