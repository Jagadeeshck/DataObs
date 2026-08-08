# Data contracts

Data Contracts are tenant- and environment-scoped governance entities attached to the canonical asset ID. Immutable versions progress through `draft → in_review → approved → active → deprecated → retired`; review may end in `rejected`. Enforcement is observational: `observe`, `warn`, `enforce`, or `disabled` never blocks producer writes or pipelines.

The evaluator consumes canonical schema observations, monitor results, freshness and volume evidence, asset metadata, and bounded lineage-impact references. It never queries raw rows or runs quality SQL. Unavailable evidence is excluded from scoring and cannot prove compliance. Evaluations and violations use deterministic IDs for replay.

Current contracts and health are mutable projections; versions, lifecycle events, evaluations, and violation evidence are append-only. Draft changes use Elasticsearch sequence-number/primary-term OCC surfaced as ETags.
