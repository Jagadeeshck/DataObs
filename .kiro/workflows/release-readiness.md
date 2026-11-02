# DataObs release readiness

1. Read `.kiro/specs/first-release-week/requirements.md`, `docs/kiro/FIRST-RELEASE-PLAN-2026-11-06.md` and `docs/development/team-ownership.md`.
2. Fetch latest `main`, version metadata, GitHub Releases/tags and CI runs; classify **source state**, **candidate state** and **supported-release state** separately.
3. Reconcile v1.0.0 / ES 9.5.5 vs stale v0.2.0 / ES 9.4.2 claims.
4. For failed mandatory checks record exact first error and owner; cluster cascades and preserve passes.
5. Output updated six-team actions and merge order, Gate 0 blockers, timing risk and GO/NO_GO without promoting status.
