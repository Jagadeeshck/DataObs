---
inclusion: auto
name: dataobs-domain-contracts
description: Use for Kafka streams, pathway intelligence, quality, lineage, OpenTelemetry, OpenLineage, incidents, data products or provider integrations.
---
# Domain correctness contracts

- Kafka: offsets, consumer lag, leases, checkpoints, schema compatibility, capture cadence, replay/fencing, bounded queries, explicit missing/stale/zero semantics.
- Pathways: deterministic assembly, durable watermarks, late events, partial evidence, confidence, evidence coverage, latency and SLOs; never conflate dependency and impact.
- Quality: durable monitors, checks and baselines; separate failing check from missing observation; retries and run-now bounded and tenant-safe.
- Jobs/Lineage: ingest bounded/redacted OpenLineage; deterministic jobs/runs/tasks and dataset/column lineage; cycles/truncation disclosed.
- Incidents: dedup, OCC, append-only audit, notifications with unknown-outcome safety, no blind external retry.
- Providers: feature-level declarations, checkpoint correctness, packaged runtime and live certification prerequisite for supported claims.
- Business and AI pillars: roadmap first; do not silently treat designed capability as delivered.
