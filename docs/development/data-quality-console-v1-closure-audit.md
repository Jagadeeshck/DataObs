# Data Quality Console v1 closure audit

## Scope and reconciliation

The audited repository snapshot is `232a8e0`. The complete merge commits for PR #190 (`1576c73`) and PR #194 (`9496b5e`) were compared. PR #190's evidence-aware tabbed read experience is canonical at `/quality`; PR #194's authoring, inventory and Monitor 360 are retained as nested routes. `App.tsx` now registers only one lazy `quality/*` tree. The public routes are `/quality`, `/quality/monitors`, `/quality/monitors/new`, and `/quality/monitors/:monitorId`.

Canonical endpoints include overview, inventory, findings, recommendations, coverage, runtime, monitor evidence, draft creation, enable, disable, archive, queued run, baseline reset and suppression creation. Recommendation accept/reject/defer is supported. No autonomous remediation exists.

## Trust and evidence decisions

Tenant is taken from request authentication middleware and environment from server application settings. Recommendation decisions, baseline resets and suppression creation use the authenticated principal subject. A legacy actor field is accepted only when it equals that subject; spoofed overrides fail closed. Suppression timestamps require offsets, positive duration and at most exactly 31 days.

The Console preserves available, partial, stale, missing, unknown, unavailable and not-configured meaning. Zero remains a measured value; empty collections do not establish zero; stale does not establish failure; unavailable runtime is not healthy; absent incident linkage does not establish no impact; queued is not completed; accepted recommendations do not establish monitor creation; missing baseline is not zero.

## Removed duplication and validation

Direct Quality registrations in `App.tsx` were removed. `QualityRoutes` is the sole route tree and owns all four routes. Local results are recorded in the pull request. Hosted results, workflow URL and artifact ID are unavailable locally. Certification remains `functional_unvalidated`; neither Playwright nor axe success is claimed without execution.

## Limitations and rollback

Operational evidence depends on configured providers. Hosted final-head PostgreSQL, Elasticsearch, Chromium and axe evidence remains required. Roll back this application commit/deployment; no migration was added or modified. Existing definitions and immutable history remain intact.
