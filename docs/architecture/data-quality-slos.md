# Data quality SLOs

DataObs uses the shared contracts in `packages/domain_model/slo.py`; this is an extension of Data Product SLO semantics, not a competing generic engine. An SLI is a measured value from canonical evidence. An SLO is an objective for that SLI. Asset, monitor-group, job, and Data Product scopes are bounded, and v1 has named SLI families rather than arbitrary expressions.

Every expected interval is `good`, `bad`, `unknown`, or `excluded`. Unknown is never silently good or bad. The definition selects `partial` (default), `exclude`, or `count_as_bad`. Evaluations expose all counts, coverage, evidence status, and confidence. Contract, job, dbt, schema, and monitor engines retain ownership of their rules; the SLO evaluator consumes their results.

Rolling windows evolve naturally. Calendar windows reset at their calendar boundary. Windows are limited to 1 hour through 365 days and granularities to 5m, 15m, 30m, 1h, or 1d. Backfills use original event-time expectations by default, so late arrivals cannot rewrite historical truth. Reconciliation appends a superseding evaluation rather than overwriting history.

Evaluation identity binds tenant, environment, SLO, revision, window, formula version, and evidence fingerprint. A definition mutation creates a revision and requires actor and reason at the service boundary. Historical evaluations retain that revision.

Data Product aggregation consumes canonical child evaluations and deduplicates their evaluation IDs. Unknown children are reported rather than treated as zero. A critical child in `critical` or `exhausted` state caps the product result.
