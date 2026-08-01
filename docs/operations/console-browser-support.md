# Console browser and accessibility support

Beta targets current Chromium (the CI Playwright version), Firefox, and WebKit-compatible current browsers at 320, 375, 768, 1024, and 1440+ CSS pixels. Shared surfaces use scrollable tables/breadcrumbs, wrapping header controls, viewport-bounded dialogs, visible focus, skip navigation, route titles, semantic Quick Find controls, and global reduced-motion handling.

The closure workflow runs mobile, tablet, and desktop Playwright projects and axe checks. Serious or critical axe findings fail verification. A workflow definition is not evidence: support is certified only by the exact-commit artifact, and skipped browser execution must be recorded as a limitation.
