# Job reliability runtime operations

Migration `0024_job_run_reliability_runtime` installs policy, current snapshot, expected-run current, and runtime-state indices plus append-only reliability and expected-run evaluation streams. Stop writers before rollback, retain append-only evidence, and snapshot mutable state before removing aliases or templates. Elasticsearch is mandatory for production wiring. Operators must use a secret of at least 32 bytes for cursor signing and rotate it by allowing old cursors to expire.

This increment does not claim the polling worker, lease/checkpoint recovery scenarios, hosted browser evidence, or independent certification are complete.
