# Operating Stream Intelligence

Apply migrations through the executable registry and verify terminal migration `0026_stream_anomaly_retention_intelligence`. Stop workers before rollback; retained evidence is not deleted, and current projections must be snapshotted.

Workers must run with explicit tenant/environment scopes, bounded concurrency, renewable leases and fencing. A lost lease stops mutation. Check heartbeat, lease, last cycle, failures, insufficient-data count, pending reconciliation and Elasticsearch dependency state. Retry only classified transient Elasticsearch failures with bounded jitter.

Baseline backfill is explicit, bounded by start/end and resources, dry-run capable, resumable and idempotent. It must estimate query/document count and produces no signals by default. Never run an unbounded tenant scan.

Troubleshooting order: confirm migrations/aliases, authenticated scope, evidence freshness and coverage, detector sample bounds, lease ownership, append evidence, OCC projection, pending signal and checkpoint. Missing record age or message size is an honest unavailable forecast input, not zero.

