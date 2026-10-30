# Team 5 — Sprint 4 final-hosted Console browser proof

**Release:** v0.2.0  
**Team:** Team 5 — Console and Product Experience  
**Branch:** `codex/sprint4-team5-browser-proof`

## Starting evidence

Sprint 3 PR #328 is merged. Its exact-head static Console gate passed in main CI:
typecheck, lint, formatting, unit tests, production build, bundle budget and
contract drift completed successfully.

The Sprint 3 cross-browser producer runs then exposed real browser failures
rather than static failures. Console Product Experience and Console Beta both
reported the same bounded failure families across Chromium, Firefox and WebKit:

- keyboard-first focus assumptions around the skip link;
- stale navigation selector expecting `Streams` after the route was renamed
  `Messaging`;
- horizontal overflow at the 320/375 responsive widths;
- the 768 px acceptance case treating an exact desktop/tablet breakpoint as
  mobile while the shell contract is `max-width: 767px`;
- a serious WCAG color-contrast violation for links inside dark evidence
  banners;
- strict-mode/hidden-option Playwright selectors that do not identify the
  visible product element;
- supportability assertions that combine separate cells or match duplicate
  navigation/content text.

No accessibility rule will be disabled and no domain API or health semantic will
be changed to close these failures.

## Fixture boundary

The release fixtures remain under `ui/dataobs-console/e2e/` only. They may
model public bounded API responses for browser acceptance, but they are not
production fallbacks and do not constitute integrated API proof.

## Integrated Console-to-API smoke

The separate Team 0 production-stack browser gate remains blocked before
Playwright. Team 0 Sprint 3 retained Kind diagnostics show the API pod
CrashLooping with:

`ModuleNotFoundError: No module named 'scripts'`

The importing path is `src/api/platform_lifecycle_routes.py`, which imports
`scripts.release.current_terminal_migration`; the production API runtime image
does not currently contain `scripts/`. This is a packaging/runtime-image
defect, not a Console fixture or UI defect. Any correction to the shared API
image requires Team 0 review and must not alter domain semantics.

## Proof requirements

This PR is not complete until one exact head SHA has:

- Console typecheck, lint, format check, unit tests, build and bundle checks;
- Chromium, Firefox and WebKit release acceptance;
- 320, 375, 768, 1024 and 1440 CSS-pixel checks;
- login/context, Command Center, Quality, Jobs, Run 360, Lineage, Streams,
  Pathways and Incidents journeys;
- serious/critical axe acceptance and keyboard/focus coverage;
- retained Playwright JUnit, traces/reports and browser/viewport provenance;
- independent artifact verification;
- separate integrated Console-to-API smoke result;
- visible Console version 0.2.0.

Historical Sprint 3 evidence is diagnostic only and will not be relabelled as
Sprint 4 proof.
