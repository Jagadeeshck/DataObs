# Job and run reliability

Reliability v1 extends the canonical job/run model rather than creating a second domain. A versioned policy identifies schedule provenance, timezone, schedule and SLO limits. A bounded generator emits deterministic expected-run identities for configured/provider interval and cron schedules. Event-driven, ad-hoc, external and unknown schedules never generate automatic missing findings; inferred schedules require confidence of at least 0.8.

Evaluations are append-only. Current expected-run and job snapshots are projections, so a late actual run produces corrective evidence instead of rewriting history. The score is the weighted mean of evidenced components: `100 × Σ(component × normalized available weight)`. Unavailable or under-sampled components are excluded and disclosed. Scoring requires the configured minimum sample and component count; confidence combines evidence coverage, sample coverage and schedule confidence.

All production persistence is behind a tenant/environment scoped repository. Production uses Elasticsearch; the memory adapter is test/demo only. Search continuation tokens are HMAC authenticated and bind resource, scope, filters, sort, values, issue time and expiry.
