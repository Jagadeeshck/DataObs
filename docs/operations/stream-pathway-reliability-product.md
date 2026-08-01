# Operating stream/pathway reliability

Start the reliability worker only after migration 0023 is applied and aliases resolve. A cycle acquires a tenant/environment lease, reads at most 200 due definitions, queries only the definition window, persists append-only evaluation evidence, updates status, then advances the checkpoint. Stop with SIGINT or SIGTERM; leases safely expire. Retry only transient Elasticsearch failures with bounded exponential backoff and jitter.

Runtime health must report lease and Elasticsearch state, due/evaluated/skipped counts, latest success/failure, consecutive failures, and checkpoint state. `not_advanced` after an evaluation failure is correct. Troubleshoot missing aliases, expired leases, stale fencing tokens, source projection freshness, and rejected unsupported metrics in that order.

Rollback stops workers and API writers, retains evaluation/signal evidence, snapshots current status, and removes resources only after review. Migration 0023 has retention intent but lacks explicit field templates/ILM operations; a future additive migration is required before production certification. Exact-commit hosted evidence is also outstanding.
