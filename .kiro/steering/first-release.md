---
inclusion: auto
name: first-release
description: Use for first release, v1.0.0, release candidate, certification, CI gates, packaging, security evidence, release readiness, release week or publication.
---
# Week of 2–6 November 2026 — first release

Target **Friday 6 November 2026** subject to a protected GO decision. Do not assume October's v0.2.0 gate results certify v1.0.0 or Elasticsearch 9.5.5.

**Gate 0:** reconcile app/chart/Console/client/Elastic versions; confirm source of truth; fix current main CI, migrations, Compose and Kind smoke, restore, OIDC, tenancy, API/Console. **Gate 1:** freeze exact SHA only after passing required shared checks. **Gate 2:** dispatch Teams 1–5 real/hosted certification on same SHA and independent artifact verification; certify a bounded platform. **Gate 3:** security PASS, verified recovery, supported platform, SBOM/provenance/signature and install. **Gate 4:** protected authority GO => publish immutable tag/artifacts; otherwise report NO_GO and optionally label internal evaluation candidate.

Read `docs/kiro/FIRST-RELEASE-PLAN-2026-11-06.md`, `.kiro/specs/first-release-week/` and current release authority docs before action.
