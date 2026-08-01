# HA, restart, upgrade and rollback certification

`kind_smoke_test.sh` and `helm_upgrade_test.sh` are the authoritative bounded harnesses. They require explicit digest-pinned test values and an external Elasticsearch endpoint; the chart never installs Elasticsearch. Missing Kind, kubectl, Helm, images or infrastructure exits as skipped/not passed rather than manufacturing success.

The hosted rehearsal must retain evidence for fresh install, API/Console readiness, worker startup, idempotent migration rerun, API and worker restarts, one replica replacement, unchanged and safe-change Helm upgrades, Kubernetes resource rollback, replica-permitted availability, durable Elasticsearch state, no duplicate migration/evidence, graceful termination and lease release/expiry. Every readiness loop uses Helm/kubectl timeouts and failure diagnostics.

Helm rollback restores Kubernetes resources only. Forward Elasticsearch migrations are not reversed; compatibility with the previous application version must be established before rollback. Locally defined harnesses are not hosted validation. Availability, recovery, disruption budgets and rolling behavior remain pending until an exact-commit hosted artifact records the environment and results.
