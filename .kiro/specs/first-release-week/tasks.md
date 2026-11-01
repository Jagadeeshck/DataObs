# Implementation tasks — DataObs v1.0.0 release week (2–6 Nov 2026)

Check boxes only after exact-commit hosted evidence. Owner and merge dependency shown in
parentheses. Detailed execution steps in `.kiro/strategy/first-release-execution-plan.md`.

## Gate 0 — Shared platform (Team 0, Monday–Tuesday)

- [ ] T0-01: Reconcile version truth — app/chart/Console/Python/ES all at 1.0.0/9.5.5 (Team 0) ✅ done on release branch
- [ ] T0-02: Fix shared CI failures (migrations, API startup, compose validation, docker-validation job) (Team 0)
- [ ] T0-02b: Helm lint + Kind smoke + upgrade + rollback pass against ES 9.5.5 (Team 0)
- [ ] T0-03: Backup/restore workflow passes with destructive test + tenant isolation verified (Team 0)
- [ ] T0-04: Security workflow passes — OIDC/JWKS hosted, tenant A/B/C denial proven, SBOM/provenance/signatures (Team 0)

## Gate 1 — Console baseline (Team 5, Monday–Tuesday)

- [ ] T5-01: Console quality CI passes — typecheck, lint, prettier, vitest, build, bundle-check (Team 5; before T1/T2 browser evidence)
- [ ] T5-02: Release-critical Playwright + axe journeys pass on real API (v1.0.0 labels updated ✅) (Team 5)

## Gate 2 — Domain certification (Teams 1–3, Tuesday–Wednesday)

- [ ] T2-01: Quality signal path hosted: monitor → OTel → ES → finding → incident → retrieval (Team 2; after T0/T5)
- [ ] T2-02: Job/run and lineage hosted evidence passes (Team 2)
- [ ] T2-03: Data Products membership + reconciliation hosted evidence passes (Team 2)
- [ ] T1-01: Kafka observer + pathway intelligence hosted with real Kafka + tenant isolation (Team 1; after T0/T5)
- [ ] T1-02: Stream 360 + Cluster 360 + Connector/Schema 360 Console Playwright + axe passes (Team 1)
- [ ] T3-01: Incident OCC + notification safe outcomes + approval-bound automation verified (Team 3; before final E2E)

## Gate 3 — Integration and provider matrix (Team 4, Wednesday)

- [ ] T4-01: Integration SDK certification passes; provider capability matrix is truthful (Team 4)
- [ ] T4-02: Collection Manager marked experimental (no unsupported claims) (Team 4)

## Gate 4 — Final certification (Team 0, Thursday–Friday)

- [ ] T0-05: Merge all verified PRs in dependency order; rerun complete Gate 0 on final SHA (Team 0)
- [ ] T0-06: Freeze exact candidate SHA after Gate 0 green; dispatch canonical Team 1–5 release workflows (Team 0)
- [ ] T0-07: Independent verification of all artifacts — digest, SHA, attempt, ES version, no mandatory skips (Team 0)
- [ ] T0-08: Release authority GO → publish v1.0.0 tag + signed images; otherwise NO_GO + blocker report (Team 0)

## Post-v1.0.0 (Layer B — Q4 2026)

- [ ] B1: Elastic ML anomaly detection on quality monitors (migration 0034, `src/quality/checks/ml_anomaly_check.py`)
- [ ] B2: Watcher-driven alerting replacing APScheduler poll (Elastic Enterprise Watcher)
- [ ] B3: Built-in quality check templates (freshness, row count, null rate, schema drift, uniqueness)
- [ ] B4: Asset catalog / semantic search (migration 0036, ELSER + ESRE)
- [ ] B5: dbt artifact ingestion → assets + quality findings via OpenLineage pipeline

## Delivery order

Shared infra T0 → Console T5 → Quality/Data T2 → Streams T1 → conditional T3/T4 →
T0 final certification. Teams may diagnose in parallel; merges follow dependency order.
Any source change after SHA freeze restarts certification.

## Stop conditions (any one = NO_GO)

- Migration immutability check fails
- API or Console won't start clean from scratch
- Destructive restore missing or fails
- Any tenant cross-access in hosted run
- OIDC invalid or wrong in production mode
- Playwright/axe missing or has serious/critical violations with real API
- Any mandatory test skipped and counted as pass
- SBOM / signatures / provenance absent or unverified
- Release authority returns NO_GO
