---
name: release-certification
description: Freeze and certify a production release candidate with exact-SHA GitHub evidence and protected GO authority.
---
# Release Certification

1. Start with current `main`, release metadata and GitHub workflow status. Never infer GO from tag/version or local checks.
2. Reconcile v1.0.0 / Elastic 9.5.5 against old v0.2.0 and ES 9.4.2 release docs/workflows; record compatibility decision.
3. Run shared CI, real clean-install migrations, Kind/Helm, MVP, auth/tenant isolation and destructive restore.
4. Require Gate 0 verifier GREEN before freezing one exact SHA; identify canonical authority command from repo.
5. Dispatch required Teams 1–5 workflows (workflow_dispatch where required), independently verify SHA/run/attempt/tests/skip counts.
6. Run supported-platform staging, OIDC/TLS, browser/axe, security release gate, SBOM, signatures, provenance, digest install.
7. Publish only after protected authority GO. If NO_GO, report specific blockers and never publish supported status.
**Output:** immutable candidate manifest, evidence matrix and formal decision.

**Always:** respect `.kiro/steering/safety-and-evidence.md` and the canonical team ownership map. Use real source, current main and exact-SHA proof.
