# Team 5 v0.2.0 Sprint 3 Console closure

**Team:** Team 5 — Console and Product Experience  
**Branch:** `codex/sprint3-team5-console-closure`  
**Release:** `v0.2.0`  
**Starting main:** `855345eb02250f9a738abe44bd520247243032bf`

This closure starts after merged PR #321 and does not duplicate its cross-browser,
fixture, accessibility, or CSS work.

## Hosted failures reviewed

The supplied failed runs are:

- Console Product Experience: `40869887912`
- Data Quality Console: `40869888220`
- Console self-observability: `40869888337`
- Administration access Console: `40869888164`
- Team Delivery Foundation: `40869888062`
- Main CI: `40869888121`

The first common Console failure is `pnpm format:check`. TypeScript and ESLint
complete successfully before Prettier reports these three files:

- `e2e/console.spec.ts`
- `e2e/fixtures/release.ts`
- `e2e/release-critical-journeys.spec.ts`

Because formatting stops execution before build/Playwright, downstream missing
browser/JUnit evidence is a consequence rather than evidence that the browser
journeys themselves failed.

The current `console-beta-closure.yml` on main contains an explicit diagnostic
that runs Prettier on exactly those three files and prints the resulting diff
before failing. Sprint 3 uses that hosted output as the canonical remediation
instead of guessing formatting changes.

## Boundaries

- No new product capability.
- No Team 1–4 domain contract changes.
- No production fixture fallback.
- No accessibility/test weakening.
- No route-registry or generated-API contract changes.
- Team 0 retains shared release-workflow authority.

## Exit

The branch remains release-neutral until the exact final SHA has passing
Console static/build gates, Chromium/Firefox/WebKit acceptance, required
responsive widths, serious/critical axe acceptance, security checks, retained
JUnit/Playwright evidence, and independent verification.
