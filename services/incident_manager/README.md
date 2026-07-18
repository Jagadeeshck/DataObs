# Incident manager

Normalizes PostgreSQL scanner, freshness, quality, source-health and OpenLineage signals into versioned `Finding` records, then applies deterministic deduplication, correlation and explainable severity to maintain DataObs incident state. Raw events are referenced by ID; mutable incident state stores safe summaries only.
