# Operating stream and pathway reliability

Run the Team 1 worker with a stable, non-secret worker identity. Health reports configuration, lease state, due/evaluated/skipped definitions, latest success/failure, failures, checkpoint state, and Elasticsearch availability; it must never report URLs or credentials.

Workers acquire a 90-second tenant/environment lease and fence every persist and checkpoint. Evaluation queries must use the exact window, fixed aliases, source allowlists, and at most 200 definitions per pass. Stop signals finish no new definition after shutdown is requested. Retry transient dependency failures with exponential backoff and bounded jitter; deterministic evaluation IDs make a repeated append idempotent.

Alert on a contended lease that outlives its expiry, repeated `not_advanced` checkpoints, or consecutive runtime failures. `no_data`, `stale`, and `error` require investigation and are not health. Rollback: disable scheduling, wait for leases to expire, snapshot current status, retain append-only evaluation/signal streams, then use the migration rollback plan. This system does not remediate.
