# Console self-observability v1 audit

**Audited base:** `5bd728f89efb49cea2e1c5d70640c1245761d7dc` (the PR #206-equivalent merge-conflict repair, `Fix committed merge conflicts and restore main integration`). The base had no conflict markers according to the repository checker; the broad grep also identified decorative `====` headings that are not conflict markers.

## Existing implementation

The startup path was `index.html` → `main.tsx` → React Strict Mode → `App` → product context → browser router → lazy route manifest → `AppShell`. There was no startup telemetry. `RouteBoundary` contained render/import errors but intentionally did not report them; `RouteError` displayed raw error messages. Global errors and rejected promises were unhandled.

Most capability clients use `api/transport.ts`, which generated `X-Request-ID`, loaded an OIDC bearer token, and fetched with tenant context. Direct fetch bypasses existed in authentication (`oidc.ts`, `state/context.tsx`), pathway and quality mutations, and Integrations. There was no browser trace context, safe route templating, request duration, cancellation classification, response request-ID correlation, or propagation allowlist. Shared transport is the v1 instrumentation adoption point; auth/IdP traffic intentionally remains outside trace injection.

Runtime configuration existed as a Helm ConfigMap JavaScript object, but it was neither mounted into the Console pod nor loaded by `index.html`. CSP permitted only same-origin connections. No browser exporter configuration existed. The production Vite build used `sourcemap: false`; this safely avoided public maps but offered no private symbolication artifact.

## Performance and test baseline

Vite emitted route chunks and warned only above 900 kB. `bundle-check.mjs` enforced total and per-file budgets, but no explicit CSS, route-count, startup-journey, request-count, duplicate-request, memory, or long-task gate existed. Cytoscape flow/lineage graphs, Elastic Charts, inventory tables, repeated polling, and large route modules are the primary long-render risks. Playwright and axe scaffolding covered product journeys but had no mock OTLP receiver, malformed telemetry, diagnostics, redaction, trace correlation, Web Vitals, collector outage, or chunk-failure journeys.

## Security, operations, and evidence gaps

OIDC tokens, tenant IDs, email/display names, URL query filters, request bodies, and backend errors are present in browser memory and therefore must be structurally excluded rather than post-processed. Cross-origin OTLP would require narrow CSP `connect-src` and collector CORS; same-origin gatewaying avoids widening the default. The existing collector configs have no explicitly hardened browser receiver, origin validation, browser rate limit, or browser-specific redaction, so production enablement remains a Team 0 deployment decision. Existing Console workflows generated exact-commit evidence but did not capture OTLP, redaction, source-map exposure, performance budgets, package versions, or browser telemetry configuration.

## Selected remediation

This milestone adds opt-in runtime configuration, minimum official OpenTelemetry tracing/export packages, stable manifest route spans, shared-transport API spans, bounded Web Vitals/long tasks, global and React error capture, a machine-readable attribute policy, deterministic redaction/rate control, an admin-only diagnostics route, deterministic asset budgets, and an exact-commit workflow. It deliberately does not instrument IdP endpoints or capability-owned request bodies. Public source maps remain disabled.
