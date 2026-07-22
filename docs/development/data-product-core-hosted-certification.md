# Data Product core hosted certification

> PR #130 added typed operation-state, in-memory CAS, and traversal helper foundations only. This PR implements the production Elasticsearch runtime, integrates real repair handlers and workflows, completes APIs and Product 360, and produces retained hosted certification evidence.

## Certification matrix

This audit is deliberately fail-closed: a local result is not hosted certification. Release readiness remains **blocked** and the next milestone is **Data Product SLOs, reliability, and coverage**.

| Capability | PR #130 state | Production gap | Required implementation | Unit/property | Elasticsearch | Browser/axe | Security | Hosted artifact |
|---|---|---|---|---|---|---|---|---|
| Manual/proposal/exclusion pending recovery | immutable decisions exist | typed lookup/recovery incomplete | reuse pending evidence; append only terminal evidence | membership suites | recovery scenarios | Members journey | takeover/leakage | recovery evidence |
| Dependency immutable replay/result snapshot | replay reads current edges | original result can be lost | bounded immutable product and edge snapshot, verified on replay | coordinator immutable-replay test | later-mutation replay | editor replay | poisoning | operation/result evidence |
| Empty replacement/current snapshot/batch validation | coordinator foundation | PIT certification pending | complete bounded snapshot and one scoped validation batch | coordinator tests | >200 edges | dependency list | oversized input | snapshot evidence |
| Pending payload/product OCC/projection OCC | pending event precedes product write | full CAS fencing pending | durable plan, product token, restartable targets | coordinator tests | fault injection | pending status | stale worker | OCC evidence |
| Partial writes/terminal/idempotency/CAS | inspect-only reconciler | crash matrix incomplete | bounded claimed recovery at every boundary | reconciliation tests | two reconcilers | operation history | takeover | reconciliation evidence |
| Tombstones/re-add | tombstones supported | retained-history proof pending | no deletes; deterministic remove/re-add metadata | remove-all test | remove/re-add | removal history | tenant isolation | tombstone evidence |
| Frontier accounting/timeout/cycle/consistency | frontier foundation | paged request accounting pending | each page charged; full path and explicit reason | frontier tests | >1,000 edges | controls/table | amplification | traversal evidence |
| Impact | evidence summary | source completeness pending | available/partial/unavailable from real evidence | impact tests | mixed sources | Impact panel | sentinel | impact evidence |
| Operation API and signed dependency/revision pagination | cursor foundation | hosted drift proof pending | scoped status and signed exact sort tuple | cursor tests | concurrent paging | load-more focus | tamper/expiry | API evidence |
| Product 360 workflows | membership components exist | remaining panels pending | actionable Members, Dependencies, graph/table, Impact, revisions | component tests | real API | Playwright/axe | stored XSS | browser evidence |
| Real stack and dynamic manifest | jobs declared | hosted run not yet available | ES 9.4.2, Chromium/axe, dedicated security, generated run manifest | unit job | Elasticsearch job | browser job | security job | manifest.json |
| Review threads | inherited threads open | hosted proof required | reply with SHA, test, job, artifact before resolution | n/a | n/a | n/a | n/a | review references |
| Operation-state mapping and CRUD | dataclasses and memory storage | production repository omitted | create-or-verify state in the released strict envelope | state transitions | writer/query contract | operation details | state poisoning | state evidence |
| Immutable-history mapping/create-or-verify | memory dictionary | no create-only Elasticsearch evidence | deterministic scoped IDs and canonical conflict verification | canonical equality | immutable create conflict | history panel | history poisoning | history evidence |
| Claim expiry/reclaim and stale-worker fencing | memory CAS | no Elasticsearch OCC | `_seq_no`/`_primary_term`, generation and owner fencing | monotonic generation | two workers/takeover | recovery state | claim takeover | claim evidence |
| Workflow state creation and checkpointing | facade only | mutations not integrated | pending history, durable plan, pending state and checkpoints at boundaries | fault matrix | partial-state recovery | pending workflow | reference poisoning | recovery evidence |
| Manual/proposal/exclusion/dependency/lifecycle recovery | evidence inspection | no typed repair registry | operation-specific idempotent handlers | handler order | crash boundary matrix | manual reconcile | stale mutation | handler evidence |
| PIT dependency snapshot | bounded current reads | no point-in-time isolation | PIT, `search_after`, hard maximum and checksum | checksum | concurrent write | dependency evidence | PIT failure | snapshot evidence |
| Relevant-cycle and physical-page accounting | helpers only | loader not connected | shared budget and one charged request per physical page | shared budget | indirect multi-page cycle | graph controls/table | amplification | traversal evidence |
| Signed pagination | cursor foundation | incomplete resources/bindings | exact `_id` sort tuple bound to route, scope, filters and expiry | cursor binding | concurrent mutation | next-page actions | tamper/replay | pagination evidence |

## Operation ordering

The dependency coordinator reserves a scope-bound fingerprint, replays only an immutable completed operation, reads the complete projection, validates upstreams in one bounded batch, writes pending evidence, acquires the Data Product ETag/revision serialization token, applies an idempotent projection plan, writes terminal evidence, and completes idempotency. This is a recoverable multi-index workflow, **not** a cross-index transaction.

No migration 0017 is introduced: the existing operation/revision envelope is used. Migrations 0001–0016 remain immutable.

## Hosted evidence policy

`artifacts/data-product-core/manifest.json` is generated by the evidence job. A manifest without a GitHub run URL, successful required jobs, retained artifact identifiers and hashes is non-certifying. Inherited review threads may only be resolved after those fields exist and their specific test jobs pass.

## Reconciliation runtime status

The reconciliation runtime uses scope-bound immutable plans/results, excludes active claims from scans, fences claim ownership by tenant, environment, product, owner and generation, and exposes bounded single/batch CLI execution. The focused workflow uses Elasticsearch 9.4.2 and dedicated contract, unit, integration, security, evidence, and fail-closed summary jobs. Until that workflow publishes a run URL and retained manifest, these changes are **not hosted certification** and release readiness remains **blocked**. The next milestone is Data Product APIs, Product 360, browser/security, and final hosted core certification.
