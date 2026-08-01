# Console browser certification

The `Console Product Experience v1` workflow installs frozen dependencies and
the official Playwright Chromium build, then runs generation drift, typecheck,
lint, formatting, unit/component tests, the production build, bundle budget,
Playwright/axe journeys, and repository policy gates. It uploads exactly one
producer artifact named `console-beta-integration-v1-evidence` and an
independent job verifies the downloaded artifact against the selected head SHA.

The mocked browser environment must satisfy trusted `/api/v1/auth/me` and each
capability API contract; production fixtures are forbidden. Reports retain
Playwright output, screenshots/traces on failure, axe results, console errors,
route count, bundle inventory, tool versions, gate summaries, timestamp, known
warnings, and any explicit skips. Browser installation failure is a failed gate,
not a reason to disable testing.

Local execution (`pnpm playwright`) is diagnostic only. Certification requires
a successful hosted exact-commit run, retained artifact ID, matching producer
SHA, and successful independent verification. No such final-head proof was
available during the 2026-08-01 audit, so status remains
`functional_unvalidated`.
