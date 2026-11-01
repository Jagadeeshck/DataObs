---
inclusion: always
---
# DataObs technology and engineering choices

- Python backend, API in `src/api`, `services/*`, `packages/*`; dependencies via `requirements*.txt`, pytest, Black (120), Ruff, mypy.
- React 18 + TypeScript + Vite, Elastic EUI/Charts, React Router, Vitest, Playwright/axe. Console package in `ui/dataobs-console/` uses pnpm 10.
- Elasticsearch/Kibana authoritative. The 2026-10-31 main commit changed Elastic Stack target to **9.5.5** and `RELEASE.md` to v1.0.0; historical test/docs may still pin 9.4.2. **Verify actual configured support and hosted results; never silently mix versions.**
- OpenTelemetry SDK/Collector/OTLP and OpenLineage; Kafka observer; optional collection providers. PostgreSQL and Kafka for applicable integration tests.
- Docker Compose (MVP, demo, certification), Docker image builds, Helm/Kubernetes (Kind and external secured ES) for release.
- CI and certification in `.github/workflows/`, `scripts/certification/`, `scripts/release/`, evidence reports, product ledger.

## Engineering rules
- Extend existing service / API / schema patterns; search before creating new abstractions.
- Do not rewrite previously released Elasticsearch migration definitions/checksums. Use additive forward migration plus migration/reindex plan when needed.
- Security defaults: OIDC/JWKS where supported, least privilege, deny cross-tenant, tenant + environment scoping, secret redaction, audit and bounded input.
- Evidence must include source SHA, workflow/run attempt, JUnit, independent verifier results and exact Elastic version. A skipped mandatory test is not a pass.
- No unsupported API contract, broad provider compatibility, healthy status or feature completion claims.
- Run smallest affected tests first, then real integration, browser, and release gates when appropriate.
