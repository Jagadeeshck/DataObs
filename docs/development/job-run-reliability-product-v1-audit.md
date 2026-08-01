# Job/run reliability product v1 implementation audit

Audited base: `043a4e368d40f0fe04d8d48610b1af613985357b`. Final SHA is recorded by the pull
request and exact-commit workflow after commit. PR #207's canonical contracts,
schedule generator, scorer, cursor and migration 0024 were reused; no new reliability
domain and no migration were created.

This increment expands the deterministic repository with immutable policy history,
idempotent expectations/evaluations/snapshots, current history, lease fencing,
monotonic checkpoints and durable idempotency semantics. Elasticsearch writes use
fixed aliases, create-only append evidence and sequence-number OCC for policy updates.
It adds exact/nearest-window association, an evidence-aware run evaluator and bounded
cycle orchestration that advances checkpoints only after writes.

Configured/provider schedules override inference through policy selection; inferred
schedules below the established confidence threshold, ad hoc, event-driven and
unknown schedules produce no automatic expectations. Association is scoped to
tenant, environment and job. Unknown duration and retry evidence remain unavailable,
not passing or zero; correlated quality evidence is explicitly not called root cause.

Local tests and their results are reported in the pull request. Hosted workflow URL,
artifact ID and independent verification are unavailable until CI runs at the final
head. The capability is therefore **not certified** and **not asserted production
ready**. Remaining limitations include production dependency composition, full PIT
read APIs, Console product surfaces, Playwright/axe and hosted evidence.

Rollback: stop reliability workers, revert this commit, retain append-only evidence,
and do not remove or modify migration 0024 resources.
