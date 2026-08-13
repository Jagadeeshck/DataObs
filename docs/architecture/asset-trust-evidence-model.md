# Asset trust evidence model

Trust consumes canonical evaluations and never scans raw rows. Every input identifies its source, reference,
dimension, observation time, status, confidence, coverage, reason codes, and `derived_from` provenance.

Within each dimension the deterministic hierarchy is production SLO evaluation, canonical domain evaluation,
then canonical monitor/job/contract evaluation. Higher-level evidence claims its underlying references, so the
same freshness monitor cannot be counted again through a freshness SLO; the same rules cover dbt/canonical and
job/SLO overlaps. Stale and not-configured evidence are gaps, not bad data. No contract is not compliance.

History is immutable and identified by tenant, environment, asset, window, policy/version, evidence fingerprint,
and calculation version. This preserves interpretation after a policy revision and makes replay idempotent.
