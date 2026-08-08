# Operating Stream Intelligence production runtime

Apply the executable migration registry and verify terminal migration `0026_stream_anomaly_retention_intelligence`, its five mutable indices, four data streams, templates, aliases, and lifecycle policies. Run one worker per trusted tenant/environment scope; competing workers are safe through lease fencing.

Monitor heartbeat, lease expiry, failed detectors, pending reconciliations, pending signals, dependency status, and consecutive runtime failures. `stale` means evidence is older than the configured threshold; `insufficient_data` means minimum evidence was not met. Neither is healthy.

On shutdown, stop scheduling, finish or abandon the current detector safely, and release the lease. On lease loss, stop all mutation immediately. For recovery, rerun the bounded cycle: deterministic append identities suppress duplicates and the unadvanced checkpoint anchors reconciliation.

Baseline backfill must specify tenant/environment, resource type and selector, start/end, detector selector and a maximum resource count. Dry-run first and report matched resources, queries and estimated points. Backfills are checkpointed, idempotent and suppress transition signals by default.

Rollback stops workers and removes routing/aliases only after snapshotting projections. Append-only evidence follows migration retention and is not deleted. Local evidence must not be represented as hosted certification evidence.
