# Team 5 v0.2.0 Console route acceptance matrix

This matrix records **Console acceptance scope**, not backend production certification. Capability support remains authoritative in the product ledger and release evidence.

| User journey / route | Owner | v0.2.0 Console role | Acceptance evidence | Current disposition |
| --- | --- | --- | --- | --- |
| Login / auth callback / logout | Team 0 + Team 5 shell | Required | unauthenticated/authorised routing, shell auth context, session failure behaviour | hosted pending |
| Command Center `/` | Team 5 | Required | shell load, unknown/unavailable evidence, keyboard, Axe, responsive matrix | hosted pending |
| Assets `/assets` | Team 2 | Required observation | browser smoke/deep-link; Team 2 owns asset semantics | hosted pending |
| Asset detail `/assets/:assetId` | Team 2 | Required observation | detail/deep-link acceptance; missing evidence remains explicit | hosted pending |
| Data Quality `/quality` | Team 2 | Required observation | shared browser acceptance plus Team 2 focused workflow | hosted pending |
| Monitor inventory `/quality/monitors` | Team 2 | Required | loading/empty/error/deep-link acceptance | hosted pending |
| Monitor authoring `/quality/monitors/new` | Team 2 | Required safe workflow | labels, validation, keyboard; no contract changes by Team 5 | hosted pending |
| Monitor detail/investigation `/quality/monitors/:monitorId` | Team 2 | Required | evidence states and investigation handoff | hosted pending |
| Jobs `/jobs` | Team 2 | Required | inventory/deep-link browser acceptance | hosted pending |
| Job 360 `/jobs/:jobId` | Team 2 | Required | context, quality/reliability handoffs | hosted pending |
| Run 360 `/runs/:runId` | Team 2 | Required | run evidence and deep-link acceptance | hosted pending |
| Run comparison `/runs/compare` | Team 2 | Optional release investigation | route smoke; capability truth remains Team 2 | hosted pending |
| Lineage `/lineage` | Team 2 | Required investigation | cycle/truncation/partial-state UI plus browser acceptance | hosted pending |
| Messaging `/streams` | Team 1 | Required observation | inventory, provider truthfulness, browser/Axe | hosted pending |
| Stream Reliability `/streams/reliability` | Team 1 | Conditional on capability evidence | route smoke; unvalidated runtime must not be shown as supported | hosted pending |
| Stream Intelligence `/streams/intelligence` | Team 1 | Conditional on capability evidence | route smoke; missing/unknown evidence truthful | hosted pending |
| Stream/Kafka detail routes | Team 1 | Required where authoritative | deep links and accessible alternatives | hosted pending |
| Pathways `/pathways` | Team 1 | Required investigation | route/deep-link acceptance and partial/truncated state | hosted pending |
| Pathway detail `/pathways/:pathwayId` | Team 1 | Required investigation | detail/deep-link acceptance | hosted pending |
| Incidents `/incidents` | Team 3 | Required response | inbox, tenant/environment scope, permission gate | hosted pending |
| Incident workbench `/incidents/:incidentId` | Team 3 | Required response | investigation-to-incident handoff; mutation semantics remain Team 3 | hosted pending |
| Event Storms | Team 3 | Conditional | route smoke; capability certification remains Team 3 | hosted pending |
| Integrations `/integrations` | Team 5 + Team 4 contracts | Required setup | truthful empty/unconfigured state, browser/Axe | hosted pending |
| Integration detail | Team 5 + Team 4 contracts | Required where configured | safe detail/deep-link; no credentials | hosted pending |
| Onboarding `/onboarding` | Team 5 | Required first run | keyboard, validation, actionable configuration errors | hosted pending |
| Global Search `/search` | Team 5 | Release investigation aid | shared shell/browser smoke; server-bounded providers only | hosted pending |
| Investigation `/investigate` | Team 5 | Required cross-capability investigation | route-aware evidence, partial-provider handling, accessibility | hosted pending |
| Data Flow `/flow` | Team 5 | Required investigation | truncated graph disclosure and accessible table alternative | hosted pending |
| Operational Dashboards | Team 5 | Optional operator surface | route smoke; no release-support inference | hosted pending |
| Administration | Team 5 + Team 0 auth contracts | Required for authorised admins only | permission isolation; direct route denial for unauthorised users | hosted pending |
| Platform Operations / Supportability / Readiness / Upgrades | Team 5 + Team 0 contracts | Admin-only | permission isolation, NO_GO/stale/unknown truthfulness, read-first UX | hosted pending |

## Release-scope presentation rule

A route may be implemented and browser-accepted while its underlying capability remains unvalidated. Team 5 must render capability availability from authoritative metadata and must not reinterpret `unknown`, `unavailable`, `not_configured`, `functional_unvalidated` or `NO_GO` as supported.

## Success path

The first-release critical path is accepted only when hosted evidence shows that an authorised user can:

1. enter the authenticated Console and select a trusted tenant/environment;
2. observe an asset or stream;
3. inspect Quality/Job/Pathway context for a failure;
4. traverse lineage or related operational context;
5. enter the corresponding Incident Inbox/Workbench without cross-tenant exposure; and
6. complete the journey with no critical browser, accessibility or security defect.

The final status of this matrix must be updated only from exact-SHA hosted evidence.
