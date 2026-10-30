# Team 2 Sprint 4 — Quality and Lineage Browser Handoff

**Starting main:** `c3d3dfe63b2d8227612dc867988db268c8b7424f`  
**Owner of Team 2 feature behavior:** Team 2  
**Owner of shared Console/browser harness:** Team 5

## Current hosted observation

On starting main:

- Data Quality Console run `41120485783` passed the Quality backend, static checks, unit tests and production build, then failed the shared browser/accessibility step.
- Lineage Console run `41120485815` passed the Lineage/Jobs backend, static checks, unit tests and production build, then failed the shared browser/accessibility step.

The shared browser failures include shell skip-link focus, responsive overflow, global navigation expectations, global color contrast, Supportability locators/states and a Streams/Pathways presentation assertion. These are not evidence of a Quality or Lineage backend defect.

## Sprint 4 Team 2 acceptance

The Team 2 workflows now execute only the Team 2 release journeys from the shared release fixture while retaining real Playwright and axe execution.

### Data Quality Console

Required journeys:

1. `Quality inventory, authoring and monitor investigation remain usable`
2. `URL tenant/environment values cannot override trusted request scope`
3. `expired or unauthorised auth context fails closed before capability data loads`

Quality runs across Chromium, Firefox and WebKit and retains JUnit plus the HTML Playwright report.

### Jobs and Lineage Console

Required journeys:

1. `Jobs, Run 360 and lineage context are reachable from the trusted scope`
2. `URL tenant/environment values cannot override trusted request scope`
3. `expired or unauthorised auth context fails closed before capability data loads`

Lineage retains its existing Chromium certification caller and now writes JUnit using the canonical `PLAYWRIGHT_JUNIT_OUTPUT_FILE` variable.

## What this does not do

This change does **not** remove the global browser requirement from the release. The Beta manifest separately marks Team 5 Console experience as mandatory, with browser/accessibility/build evidence. Team 2 does not claim that global shell, Streams, Pathways, Supportability or unrelated product journeys are green.

Team 5 should use the starting-main failures as the current shared-harness backlog while Team 2 independently closes the Quality and Lineage feature acceptance rows.
