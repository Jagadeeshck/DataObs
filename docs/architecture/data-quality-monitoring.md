# Data Quality Monitoring v1

Data Quality Monitoring uses `MonitorDefinition` as its sole definition contract. Elasticsearch stores definitions,
immutable definition history, schedules, leases, checkpoints, observations, baseline versions, evaluations, findings,
suppressions, recommendations, coverage, and runtime health. The API never hosts the scheduler.

The production path is: definition → PostgreSQL aggregate observation → baseline calculation → explainable evaluation
→ durable finding → Incident Manager correlation → configured notification. Provider errors and missing observations are
not quality breaches. Suppression retains observations and evaluations while preventing paging; recovery only updates the
finding and incident correlated to that monitor.

## Supported v1 types

The canonical capability endpoint reports freshness, volume, schema change, field null rate, field unique rate, field
distribution, field range, validation, and safe custom aggregate monitors. It reports every other broad enum value as
unsupported rather than implying execution. PostgreSQL is the only production provider. Its execution boundary permits
reviewed, single-row aggregates over allowlisted relations and identifiers, uses a read-only transaction and statement
timeout, and never persists raw rows. Schema and distribution providers remain capability-visible but will return an
unsupported provider result until configured; they are not certified by repository-local evidence.

## Scheduling and safety

The separately deployed `python -m services.monitor_runtime.cli run` process queries bounded, stably ordered due work.
Workers acquire expiring leases, use OCC-backed checkpoints, and append observations/evaluations idempotently. Intervals
are bounded from one minute through 31 days and interpreted in UTC; cron is not supported in v1. `once` performs one
bounded cycle, `health` verifies Elasticsearch, migrations, runtime resources, and providers, and
`reconcile-definitions` produces an OCC-aware plan. SIGTERM/SIGINT stops new polling before process exit.

No monitor remediates a source. Recommendations create reviewable proposals only. Monitor-as-code derives tenant and
environment from trusted runtime context and applies through the canonical repository.

## Security and limitations

Canonical `/api/v1/quality` routes use trusted OIDC tenant context and central quality/monitor permissions. IDs and every
Elasticsearch query are tenant/environment scoped. Run-now is durable, asynchronous, and idempotency-key aware. SQL,
credentials, raw values, table names, and error messages must not be telemetry dimensions or certification evidence.
There is no autonomous remediation, advanced custom-policy engine, Job/Run Explorer, Data Streams Monitoring, or HA/DR
claim in this scope.
