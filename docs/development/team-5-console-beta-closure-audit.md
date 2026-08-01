# Team 5 Console Beta closure audit

**Audit date:** 2026-08-01. **Audited workspace base:** `1297937bf66ce0d6b3d869815d1f395df5c27c1e` (`main` merge snapshot supplied for this task).

## Dependency status

PR #191, **Build DataObs Console and Product Experience v1**, is present as merged commit `7b96468b781bcd08380575187290c721777c935e`. Its recorded base parent is `9496b5e98a46b449b69e09157176588dcb9d7c9c` and head parent is `4374d2ca3ed57f3723b2b400d6f7b35fc2e1755c`. The shell, registry, product context, Command Center, Data Flow, Integrations, and Onboarding are present. The audited snapshot also contains the security merge in PR #193. The checkout has no configured Git remote or GitHub CLI, so live hosted metadata could not be independently queried; commit ancestry is the source of truth for this local audit.

## Route reconciliation findings

The prior registry grouped detail paths in `children`, while the router separately declared them. This hid duplicate/orphan risk and omitted component, configuration, parameter encoding, parent, and Quick Find metadata. The reconciled inventory is: Command Center; Data Flow; Assets/Asset 360; Streams/Kafka Cluster/Topic/Consumer Group/Connector/Schema 360; Pathways/Pathway 360; Quality/Monitors/Create/Monitor 360; Jobs/Job/Run/Run Comparison; Lineage; Incidents/Workbench; Data Products/Data Product 360; Integrations/detail; Onboarding; sign-in/callback/sign-out/unauthorised; and the shell not-found fallback. There were no duplicate rendered paths, but every detail and authentication path was absent as an independent registry record. Detail breadcrumbs previously collapsed to one generic capability crumb. Implemented incidents were incorrectly labelled `not_configured`.

## Integration findings and disposition

* **Deep links/navigation:** preserved paths, added canonical entity encoders and registry parents. Entity display names remain capability-owned; breadcrumbs use non-sensitive route labels until supplied metadata is available.
* **Context:** feature request hooks generally consume tenant/environment and refresh generation. APIs without time-range support remain current-projection views. Auto-refresh did not pause in hidden tabs (corrected in the shared context). Request cancellation remains hook-owned.
* **States/evidence:** shared evidence components distinguish missing, partial, unavailable and stale states. Capability-specific duplicates remain and require owner approval to consolidate. No evidence calculation was changed.
* **Fixtures:** fixtures are test-only under `src/test` and Playwright interception. No production fixture fallback was found. Demonstration seed scripts and dated test values are not production rendering paths.
* **Accessibility/responsive:** generic lazy text named Streams for every route; breadcrumbs lacked hierarchy; Quick Find was absent; mobile shell controls could overflow; reduced motion only covered Cluster 360. Shared fixes are included. Full axe certification remains a hosted-workflow result, not claimed here.
* **Performance:** only Streams and Data Products were lazy. Registry-driven loaders now split all capability route modules. Exact output sizes are recorded by the build/bundle commands and closure artifact.
* **Browser evidence:** Playwright definitions existed, but no retained exact-commit Team 5 closure artifact existed. Local execution does not constitute hosted evidence.
* **Owner approval:** source-evidence handoffs inside Incidents, Quality, Jobs, Pathways, and other capability-owned views; bounded entity-search API adapters; and display-name breadcrumb contracts remain cross-team work. They were not fabricated or broadly rewritten here.

## Known gaps

OpenAPI exposes inventory endpoints but no consistently bounded, tenant-scoped cross-domain search contract. Global Quick Find therefore searches registry navigation and tenant/environment-isolated recent metadata only; entity domains are truthfully unavailable. Hosted browser/axe evidence can only be certified after the workflow runs against the resulting exact commit. No Elasticsearch migration was added or changed.
