# Team 5 v0.2.0 Console release acceptance

**Team:** Team 5 — Console and Product Experience  
**Branch:** `codex/release-team5-console`  
**Target:** DataObs `v0.2.0` first-release Console acceptance  
**Audited main:** `919b1e5f1f069ceb76830b92f8eb44e423e15a90`  
**Release authority:** Team 0  
**Release decision:** unchanged; this work does not authorize a release.

## Scope and ownership

This is a stabilization and certification-closure change. It does not add a product capability or redefine Team 1–4 domain contracts. Team 5 owns the shared shell, browser harness, accessibility presentation and release UX. The only shared workflow change is the existing Console closure caller; it requires Team 0 review because `.github/workflows/` is Team 0-owned.

## Hosted failure reproduced before changes

The exact hosted failure inspected was **Console Beta closure v1** run `40671784215` on Team 2 PR #310 head `6c8df8157e367644ae5c585dbe2a3f2efdc8e1be`.

The validate job failed with ten Playwright failures:

| Failure | Classification | Disposition |
| --- | --- | --- |
| First-tab visible-focus assertion | Shared test/harness | Assert the actual skip-link focus target |
| Tenant locator matched context summary and select | Shared browser test | Use exact accessible-name matching |
| Workspace locator matched Workspace and Workspaces | Shared browser test | Use exact accessible-name matching |
| Quick Find/default button contrast | Shared Team 5 CSS | Give controls the dark Console surface |
| Navigation section-heading contrast | Shared Team 5 CSS | Use the accessible muted token |
| Flow filter contrast | Team 5 Flow presentation | Use the accessible muted token |
| Primary blue action contrast | Shared Team 5 CSS | Use dark foreground on blue |
| Data Product member/dependency journeys lacked API fixture | Browser harness; domain remains Team 2 | Add bounded test-only API fixtures |
| Supportability journeys had no trusted tenant and fell into Access denied | Browser harness; Team 0 API semantics unchanged | Supply trusted test context |
| Browser tests fell through to a dead Vite API proxy | Browser harness | Intercept auth/config and unconfigured API calls in test-only fixtures |

The independent verification job then failed because `vitest.xml` was absent. The closure workflow is corrected to invoke Vitest's JUnit reporter directly.

Repeated `/api/v1/auth/config` and `/api/v1/auth/me` proxy connection refusals were observed because the closure workflow runs the Vite preview without a live API. Production is unchanged; deterministic fixtures now satisfy only the browser test environment.

## Release-scope fixes

- Added deterministic test-only authentication, tenant/environment, shell and Data Product API fixtures under `e2e/fixtures/`.
- Kept production code free of fixture fallbacks.
- Changed ambiguous Playwright locators to exact accessible-name matching.
- Made skip-link focus the keyboard-entry assertion.
- Corrected shared control, navigation, flow-control and primary-action contrast.
- Expanded both Playwright configurations to Chromium, Firefox and WebKit.
- Added responsive release acceptance at 320, 375, 768, 1024 and 1440 CSS-pixel widths.
- Added body-overflow, narrow-navigation, stale/unavailable API, refresh/deep-link and Axe serious/critical checks.
- Updated the hosted Console closure workflow to install all three browser engines.
- Fixed Vitest JUnit evidence generation.
- Hardened independent verification so missing browser or viewport evidence fails closed.

## Truthfulness boundaries

A passing Team 5 Console run proves only the Console/browser/accessibility acceptance categories for the exact producer SHA. It does not promote a Team 1–4 capability from `functional_unvalidated`, certify Elasticsearch or OIDC, declare a supported platform, or change Team 0's release decision.

Unknown, stale, unavailable and unconfigured evidence remain distinct from healthy or supported. Release-scope browser fixtures are test-only and must never be bundled into production.

## Critical journey acceptance

See [team-5-v0.2.0-console-route-matrix.md](team-5-v0.2.0-console-route-matrix.md).

The hosted status is **PENDING** until the final branch head completes the Console closure producer and independent verifier. A local definition or passing unit test is not hosted evidence.

## Cross-team handoffs

- **Team 0:** review the shared Console closure workflow change and consume only successful exact-SHA evidence.
- **Team 1:** Streams/Pathways semantics and API defects remain Team 1-owned; Team 5 fixes only shared presentation/harness defects.
- **Team 2:** Quality/Jobs/Lineage/Data Product semantics remain Team 2-owned. The Data Product browser fixtures reproduce existing public contracts without changing them.
- **Team 3:** Incident lifecycle/automation remains Team 3-owned.
- **Team 4:** Integration provider contracts remain Team 4-owned.

## Remaining blockers before hosted rerun

- Final-head production build/type/lint/component results must be produced by hosted CI.
- Chromium, Firefox and WebKit acceptance must all execute successfully.
- Axe serious/critical results must be zero for the required release journeys.
- The independently downloaded exact-SHA artifact must verify.
- Non-Team5 v0.2.0 release gates remain governed by Team 0 and their owning teams.
