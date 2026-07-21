# Data Product proposal decision closure

> PR #125 completed manual-membership idempotency only. This PR completes proposal revisioning, proposal terminal decisions, acceptance-created membership, membership exclusion, and their API/Console/evidence workflows.

No migration 0017 required. Migrations 0001–0016 remain immutable. The stable proposal key hashes the trusted scope, entity identity, and source; canonical sorted, de-duplicated evidence determines whether the next immutable revision is created. Decision and exclusion mutations reserve the scoped key before pending evidence, use projection OCC, append terminal evidence, and then complete idempotency. Release readiness remains **blocked**; the next milestone is dependency OCC, frontier traversal, reconciliation, and final hosted certification.

| Capability | PR #125 state | Required behavior | Implementation | Unit/property | Elasticsearch | Browser/axe | Security | Hosted |
|---|---|---|---|---|---|---|---|---|
| lineage proposal identity / dependency proposal source | entity-only / incorrect | scoped stable key and distinct source | membership service | focused | CI gate | Members | focused gate | pending |
| evidence fingerprint / exact replay / changed-evidence revision | missing | canonical replay and immutable revision | membership service/repositories | focused | CI gate | Members | bounded inputs | pending |
| proposal expiry / supersession | state-only | revision-aware OCC | repositories | focused | CI gate | actions | conflict mapping | pending |
| accept actor/reason/idempotency/expected revision | missing | required and fingerprint-bound | API/service | focused | CI gate | dialog | divergent reuse | pending |
| accept pending event / creates membership / terminal event / completion / exact replay | missing | event-first repairable result | service/events | focused | CI gate | Members/history | leakage scan | pending |
| reject / expire / supersede / duplicate and decision races | state-only | shared terminal workflow | service | focused | CI gate | actions | scoped | pending |
| exclusion reservation / pending / OCC / terminal / completion / exact replay | incomplete | typed exact mutation result | service/repositories/API | focused | CI gate | dialog | divergent reuse | pending |
| proposal decision reconciliation | absent | bounded repair handlers | reconciler | focused | CI gate | history | scoped | pending |
| API / OpenAPI/client | discarded inputs | typed concurrency and replay | routes/generated schema | drift | contract | typed UI | errors redacted | pending |
| Members UI actions / decision history | absent | accessible actions and states | Console components | UI | stack | Playwright/axe gate | XSS-safe rendering | pending |
| Elasticsearch 9.4.2 / Playwright / axe / security / hosted artifacts | absent | retained focused evidence | workflow | gate | gate | gate | gate | pending |

This document records only the proposal/exclusion slice and does not certify the dependency vertical or production readiness.
