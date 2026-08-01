# Data Quality Console v1 audit

## Audit boundary

The audited base is `6d52eb8e65d47ba9c841800e1bed853de8e5c37f`. This change reuses the canonical `/api/v1/quality` monitor definitions, capabilities, coverage, runtime, evidence, recommendations, lifecycle, suppression, baseline, and run-request APIs. It does not introduce a monitoring domain, persistence model, migration, provider, credential surface, or raw SQL authoring surface.

The Console adds `/quality`, `/quality/monitors`, `/quality/monitors/new`, and `/quality/monitors/:monitorId`. Shared integration is limited to route registration, one navigation entry, capability-scoped typed API transport, and additive styles. No backend contract changed.

## Security and evidence decisions

Tenant identity is read only from authenticated Console context and is never rendered as an authoring field. Environment remains application context. Connections are opaque references. Mutation requests retain ETags, run requests generate idempotency keys, and concurrency conflicts force a refresh rather than an automatic retry. The UI uses `available`, `partial`, `stale`, `missing`, `unknown`, `unavailable`, and `not_configured`; missing evidence is labelled and never coerced to zero.

## Validation status

Local results are recorded in the pull request. The capability remains `functional_unvalidated`: a successful final-head hosted run and independently verified `data-quality-console-v1-evidence` artifact do not yet exist. Browser and axe coverage is invoked by the caller workflow, but cannot be claimed until that hosted job completes.

Known limitations: the current backend monitor-list response does not return cursor metadata and does not yet advertise filter/sort parameters; the Console forwards URL-backed filters to the server and never applies them to a loaded page. Recommendation decisions and baseline reset/suppression forms remain backend-only because the existing actor/reason contracts require a separate trusted-actor contract alignment. The overview cannot aggregate recent evaluations/findings globally because only monitor-scoped APIs exist.

## Rollback

Revert the focused commit. The additive routes, feature directory, quality client, styles, documentation, and caller workflow can be removed without a data rollback because there are no migrations or storage changes. Draft monitors created by users remain canonical backend records and can be archived through existing APIs.
