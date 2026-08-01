# Job/run reliability product completion preflight

## Audit identity

The audited base is `043a4e368d40f0fe04d8d48610b1af613985357b`. This checkout has no configured
Git remote, so `git fetch origin --prune` could not verify a newer remote head. The
locally available history contains merged PRs #207 through #212. PR #207 merged as
`577b367f0968aa601e7ddcba95d7b498131917b1` and introduced foundation commit
`f0eb7a8`. The terminal registered migration is
`0024_job_run_reliability_runtime` (24 migrations total).

## Existing foundation inspected

Migration 0024 defines fixed mutable resources for policy, current reliability,
runtime state and expected-run current projections, plus append-only job reliability,
expected-run evaluation and reliability-event streams. It is sufficient; this work
does **not** edit a released migration or add migration 0025.

The canonical domain already includes policies, schedules, maintenance windows,
expected runs, run evaluations, snapshots, schedule sources and all nine reliability
states. The schedule generator supported timezone-aware interval and five-field cron
generation, maintenance exclusions, deterministic revision-bound IDs and an inferred
confidence floor. The scorer excluded absent/under-sampled components, normalized
available weights and prevented low-confidence healthy claims.

The initial repository exposed only policy get/put and expected-run/snapshot appends.
Its Elasticsearch policy update performed a read followed by an unguarded index. Job
and run routes read `_dataobs_*` dictionaries directly; action idempotency was also a
process-local dictionary. Existing Console job scope consisted of
`JobRunExplorer.tsx`; central routes preserved `/jobs`, `/jobs/:jobId`, `/runs/:runId`
and `/runs/compare`, but no `/jobs/reliability` page existed.

Existing permissions use the approved `jobs:*`/`workflows:*` vocabulary. Existing
workflow coverage is `.github/workflows/job-run-backend.yml`; it validates the
foundation but does not provide product-v1 browser, exact-commit or independent
certification evidence.

## Gaps and ownership review

Implementation gaps are the full runtime composition, complete Elasticsearch list
and projection readers, typed production route composition, policy/reliability APIs,
Console pages, generated clients, browser/axe coverage and hosted independent
verification. Shared files that would require owner review are
`packages/domain_model/`, `packages/elastic_store/`, `src/api/app.py`, route policy,
the Console registry/client, generated OpenAPI artifacts, the capability ledger and
workflows. This change deliberately leaves released migration 0024 immutable.

No certification or production-readiness claim is made by this preflight.
