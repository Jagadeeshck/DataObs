# Team 5 — v0.2.0 Sprint 6 Console gate closure

## Scope

This Sprint 6 change is limited to Team 5 Console source, browser acceptance and
release evidence. It does not change domain API semantics, tenant isolation,
release health semantics, backend providers, migrations, or Team 0 workflow
contracts.

## Reviewed hosted failures

The requested main runs all used commit
`eb9dff57820b39c3dd33a98f834498c30f644d89`.

- Foundation `41141189220`
- Console Product Experience `41141189221`
- Data Quality Console `41141189097`
- Pathway Explorer `41141189260`
- Main CI `41141189164`

The shared Console blocker in those runs was
`pnpm format:check` on `src/styles/global.css`. Typecheck and lint had
already passed. Because formatting failed first, those runs did not provide
post-format browser assertion evidence.

## Exact-head browser failures after clearing formatting

On Sprint 6 candidate `6e080ffbad1618f9ae3658cd963059d7e0b28e7d`,
Console Product Experience reached Chromium, Firefox and WebKit and exposed five
shared assertion families:

1. Quick Find used an ambiguous generic combobox locator.
2. Command Center overflowed horizontally at 320 and 375 CSS pixels because a
   later 1100px media rule restored a two-column `.hero-metrics` grid.
3. The unavailable-state test matched a text node too narrowly instead of the
   rendered status region.
4. Supportability matched two separate "not exposed through the Console API"
   paragraphs.
5. The same failures repeated across all three browser engines; 768, 1024 and
   1440 were not implicated by the overflow assertion.

The fixes target those exact causes: accessible-name/role-based locators and a
small-screen one-column metric grid. No accessibility checks are disabled.

## Certification boundary

Browser fixtures remain test-only under `ui/dataobs-console/e2e/`. Fixture
browser proof does not replace the separate real-API certification path.

The final exact SHA must retain Playwright/JUnit/axe evidence and pass
independent artifact verification before this closure can be considered
certified.
