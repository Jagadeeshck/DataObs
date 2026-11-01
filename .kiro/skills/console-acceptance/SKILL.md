---
name: console-acceptance
description: Implement the standalone DataObs React Console and validate critical user journeys, accessibility and secure scope.
---
# Console Acceptance

1. Locate Team 5 shell or relevant domain-owned feature; avoid changing another team's API semantics.
2. Run `pnpm typecheck`, `lint`, `format:check`, `test`, `build`, `bundle:check` in `ui/dataobs-console`.
3. Run Playwright Chromium/Firefox/WebKit and axe with keyboard focus, 320/375/768/1024/1440 widths.
4. Test real auth/tenant/environment scoping, deep links, 403/404, missing/stale/unknown and error states.
5. Keep deterministic fixture responses exclusively under E2E tests; separately test integrated live Console→API.
6. Retain JUnit, traces, browser/version matrix and independently verified evidence.
**Output:** route-by-route acceptance report and exact SHA verifier result.

**Always:** respect `.kiro/steering/safety-and-evidence.md` and the canonical team ownership map. Use real source, current main and exact-SHA proof.
