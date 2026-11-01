---
name: otel-openlineage
description: Implement tenant-safe OpenTelemetry and OpenLineage ingestion, correlation and data quality to incident journeys.
---
# Otel Openlineage

1. Read current OpenTelemetry/OpenLineage architecture and canonical schemas.
2. Use bounded, redacted OTLP/OpenLineage input; no duplicate ingestion or incident engine.
3. Preserve trace/span/resource and job/run/dataset identities and tenant/environment context end-to-end.
4. Persist and correlate quality observation → evaluation → finding → canonical deduplicated incident → delivery outcome → authorized API retrieval.
5. Include replay idempotency, partial/stale/unknown inputs, cross-tenant denial and failure recovery.
6. Test with real Collector+Elasticsearch and retained `e2e-signal-path` proof, not skipped fixtures.
**Output:** schema changes, end-to-end test proof, operational runbook.

**Always:** respect `.kiro/steering/safety-and-evidence.md` and the canonical team ownership map. Use real source, current main and exact-SHA proof.
