# Operating incident correlation runtime

Run one bounded reconciliation batch with `python -m services.incident_manager.runtime once`; continuously poll with `worker`; force one batch with `reconcile`; inspect bounded backlog with `health`. Batch size is capped at 100 and idle polling is at least 250 ms. SIGINT/SIGTERM stop gracefully. Team 0 must package the worker; Team 3 does not change Helm.

On a deferred ingestion status, first verify the incident remains queryable, then inspect backlog/health and redacted logs. Retryable Elasticsearch conflicts refetch and reapply missing membership. Do not delete incidents or correlation events. Roll back by stopping runtime writers and returning to incident-only ingestion; retained projections/events are backward compatible. During rolling upgrades, run one policy version per candidate set.

Local status is `functional_unvalidated`; do not claim certification without a final-head Elasticsearch 9.4.2 workflow artifact and independent verification.
