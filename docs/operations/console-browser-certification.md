# Console browser certification

The authoritative v0.2.0 Console closure workflow is
`.github/workflows/console-beta-closure.yml`. It installs frozen dependencies
and the browser engines bundled with the pinned Playwright package, then runs
generation drift, typecheck, lint, formatting, unit/component tests, production
build, bundle checks, Playwright journeys, axe accessibility checks and
repository policy gates.

## Browser and responsive acceptance matrix

Release acceptance exercises:

- Chromium
- Firefox
- WebKit

The shared release shell is checked at these CSS viewport sizes:

- 320 × 720
- 375 × 812
- 768 × 1024
- 1024 × 768
- 1440 × 900

The full functional suite runs in every configured browser project. The
responsive release suite additionally checks body overflow, narrow navigation,
keyboard entry through the skip link, document title and serious/critical axe
violations at every documented width.

A configured project is not evidence by itself. Independent verification fails
closed unless the retained Playwright JUnit contains Chromium, Firefox and
WebKit execution and all five responsive checks.

## Browser fixture boundary

The hosted browser environment is allowed to use deterministic fixtures under
`ui/dataobs-console/e2e/`. Those fixtures satisfy trusted
`/api/v1/auth/me`, public `/api/v1/auth/config` and the bounded capability
contracts needed by a journey. They are test-only and must never be imported by
production Console modules or provide a production fallback.

Missing fixture APIs return a bounded `not_configured` response so a browser
test cannot silently depend on a dead Vite proxy. A domain journey fixture
reproduces the public API shape; it must not redefine Team 1–4 business
semantics.

## Accessibility

Axe is part of browser acceptance. Unresolved `critical` or `serious`
violations fail the required release journeys. Keyboard focus, skip navigation,
responsive product navigation, truthful loading/empty/error states and
accessible alternatives for graph-style information are also acceptance
requirements.

Accessibility must not be made green by disabling rules, hiding unsupported
states, weakening tenant boundaries or removing domain assertions.

## Retained evidence

The closure producer uploads `console-beta-closure-v1-evidence`, including
JUnit, build/bundle logs, tool versions, the exact producer SHA and Playwright
failure artifacts when available. A separate verifier downloads that artifact
and validates:

- producer SHA
- unit and browser JUnit presence
- zero required test failures
- all three supported browser projects
- all five documented responsive widths
- production bundle evidence
- secret-pattern hygiene

A browser installation failure, skipped required browser, missing report or
failed independent verifier is not a pass.

Local execution is diagnostic only. Console browser/accessibility status may be
promoted only from a successful hosted exact-SHA producer artifact and
independent verification. This evidence does not by itself promote the
underlying Team 1–4 capability or authorize a DataObs release.
