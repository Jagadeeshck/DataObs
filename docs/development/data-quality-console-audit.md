# Data Quality Console preflight audit

## Existing model and capability surface

The domain model defines freshness, volume, schema-change, field null/unique/zero/negative/cardinality/distribution/range, metric, metric comparison, validation, custom SQL aggregate, query performance, pipeline duration/missing-run, pathway latency, consumer lag, retention risk, throughput, error/DLQ rate, source availability and collector health monitor types. Provider capabilities determine which are executable; a definition being valid does not prove its provider is connected. States are draft, recommended, enabled, disabled, learning, active, degraded, suppressed, archived and error. Threshold modes are fixed, learned, hybrid, relative change, range, rate of change and missing event. Baseline methods are rolling median, MAD, robust quantiles, IQR, EWMA and same period.

Observations contain execution/monitor scope, observed time, nullable value, unit, sample count, missing-data marker, dimensions, revision, provider, bounded evidence references, collection duration, trace and schema version. Evaluations add expected range, method/window/cohort, sensitivity, sample count, confidence, cold-start state, missing inputs, exclusions, anomaly score and breach state. Findings contain IDs, tenant/environment, state, severity, definition/baseline versions, optional incident and product links; the current model has no opened, updated or recovered timestamp. Recommendations include rationale, cost, permissions, confidence, priority, duplication, gap, risk and lifecycle state. Coverage has scope, state, numerator, denominator, exclusions, category states, gaps, stale/broken monitors and recommendation count. Runtime health currently implements loop start, last successful cycle and backlog only; worker counts and lease/failure timestamps are unavailable.

## API and pagination audit

The canonical `/api/v1/quality` surface already exposed capabilities, monitor definition CRUD, history, observations, baselines, evaluations, findings, incidents, suppressions, recommendations, coverage and runtime health/backlog, with deprecated aliases. This delivery adds overview and global findings and enriches reads. The legacy repository list accepted an opaque cursor argument but deliberately rejected it at the Elasticsearch boundary. Console v1 signs route/filter/sort/tenant/environment-bound inventory cursors and applies a maximum page size of 200. The current definition repository is bounded to 200 definitions; a future projection is required for complete operational inventory aggregation without N+1 reads.

## Evidence and safety gaps

Legacy reads did not consistently include data status, observation time, coverage, confidence, warnings, missing inputs, request ID or next cursor. Definition documents do not contain finding timestamps, incident relationship evidence beyond direct IDs, observation/evaluation rollups, or a complete runtime status. These are returned as `null`, `unknown`, `not_configured`, `partial` or `unavailable`, never zero. Presentation gaps do not justify a migration.

The Console must not show connection references, credentials, authorization material, secret values, arbitrary SQL or arbitrary target parameters. Its target allowlist is asset, field, pathway, pipeline, service, source type, schema, table, columns and timestamp column. Historical definition documents and recommendation evidence payloads are excluded.

Existing permissions are `quality:read` for overview/findings/recommendations/coverage/runtime and `monitors:read` for monitor inventory/detail. Administrative override follows platform policy. No write permission or control is introduced.

## Console and certification gaps

Before this change `quality.ts` only re-exported the shared client and no Quality route, inventory, overview, findings or Monitor 360 UI existed. Console v1 is read-only and uses URL-backed navigation, abortable requests, explicit absence states, tables and textual chart alternatives. Hosted certification remains blocked until Elasticsearch 9.4.2/PostgreSQL real-stack evidence, Chromium Playwright, axe, exact-commit artifact generation and independent verification all execute successfully. Certification therefore remains `functional_unvalidated`.
