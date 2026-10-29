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


## Sprint 3 corrections

### Canonical formatter closure

The exact Prettier output printed by Team 0 PR #323 run `40951872166`
was applied verbatim to the three browser files. The resulting blob IDs match
the hosted formatter output:

- `e2e/console.spec.ts` -> `881d1ef...`
- `e2e/fixtures/release.ts` -> `d1319d2...`
- `e2e/release-critical-journeys.spec.ts` -> `55f1782...`

No test semantics changed in these formatting commits.

### Cross-browser workflow alignment

PR #321 made the default Playwright config a Chromium/Firefox/WebKit matrix.
The following named release callers still installed Chromium only, which would
fail once the formatter blocker was removed:

- `data-quality-console-v1.yml`
- `console-self-observability-v1.yml`
- `administration-access-console-v1.yml`

They now install all three configured browser engines. Unit JUnit generation
uses direct Vitest invocation, Playwright JUnit is retained, and the
self-observability/Administration independent verifiers reject missing browsers
or failed browser JUnit. Data Quality retains its existing product-evidence
verifier and writes `results/browser.xml` at the contractually required path.

### Integrated real-API browser prerequisite

Main CI's `certification-browser` job uses
`playwright.certification.config.ts`, which also defines Chromium, Firefox and
WebKit, but the job did not install those host browser binaries. A narrow
Team 0-reviewed CI change installs the pinned Playwright browser set before the
production certification stack starts. The Compose `up` path continues to own
certification-secret bootstrap.

### Release version truth

The Beta Helm chart and release target are `0.2.0`, while the Console package
and Administration System Information page still reported `0.1.0`.
`ui/dataobs-console/package.json` and the displayed Console version now report
`0.2.0`. No domain behavior or API contract changed.

## Hosted proof policy

The branch must remain a draft until the final exact SHA produces successful
hosted evidence. Prior-head runs and workflow definitions are diagnostics only.
The final report must separately record fixture-based browser/accessibility
acceptance and the integrated production-stack browser result; neither may be
inferred from the other.
