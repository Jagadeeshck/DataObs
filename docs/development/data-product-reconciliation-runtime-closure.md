# Data Product reconciliation runtime closure

> PR #131 implemented Elasticsearch operation-state and immutable-history persistence primitives only. This PR wires every scoped mutation to those primitives, implements operation-specific repair handlers, and certifies crash recovery and stale-worker fencing against Elasticsearch 9.4.2.

> PR #132 introduced generic reconciliation envelopes and dispatch scaffolding, but all operation kinds still used one non-repairing DurablePlanHandler and mutation services did not create the new operation state. This PR implements concrete projection-aware handlers and wires every scoped mutation into the runtime.

> PR #133 introduced named projection-aware handlers and partial mutation bootstrapping, but missing projection steps still returned retry rather than being repaired; proposal and exclusion workflows were not wired; synchronous paths left generic state incomplete; and real Elasticsearch fault certification remained absent. This PR closes those runtime gaps.

Release readiness remains **blocked**. Hosted artifact cells remain pending until the draft PR workflow produces downloadable evidence; local tests are not represented as hosted certification.

| Operation kind | Plan created before mutation? | State created before mutation? | Handler can create missing projection? | Handler can repair terminal evidence? | Handler can repair result/state/idempotency? | Real ES fault matrix | Hosted artifact |
|---|---|---|---|---|---|---|---|
| `manual_membership` | yes | yes | yes | generic only | yes | pending | pending |
| `proposal_accept` | yes | yes | pending | generic only | yes | pending | pending |
| `proposal_reject` | yes | yes | pending | generic only | yes | pending | pending |
| `proposal_expire` | yes | yes | pending | generic only | yes | pending | pending |
| `proposal_supersede` | yes | yes | pending | generic only | yes | pending | pending |
| `membership_exclude` | yes | yes | pending | generic only | yes | pending | pending |
| `dependency_replace` | yes | yes | pending detailed-plan application | generic only | yes | pending | pending |
| `product_lifecycle` | **no** | **no** | pending | generic only | yes | pending | pending |


## Runtime control audit

| Control | Runtime closure |
|---|---|
| operation-state / immutable-history mapping | envelope action and typed document fields distinguish immutable records; OCC metadata is not business state |
| state and history creation | create-or-canonical-verify |
| claim CAS / expiry / renewal | pending or expired claims only; generation and Elasticsearch OCC fencing |
| stale-worker fencing | scope, owner, generation, current OCC metadata, and expiry validated |
| checkpointing | deterministic checkpoint follows handler projection verification |
| terminal history and result persistence | immutable result is written before mutable completion |
| idempotency repair | scope-safe record reference on operation state |
| batch and CLI execution | bounded batch and single-operation commands under `bin/dataobs` |
| two-worker race | loser receives typed retry without handler mutation |
| tenant isolation | deterministic scoped IDs and scope-bound claims/plans/results |
| secret leakage | CLI summary contains identifiers/status only; raw idempotency keys are not persisted |

## Fail-closed gate tracker

| Gate | Status |
|---|---|
| typed plan completeness | partial; manual and proposal targets are complete, dependency/lifecycle remain gated |
| synchronous checkpoints/result/history/state completion | pending coordinator wiring |
| pending retry delegation | pending for mutation entry points |
| claim renewal | implemented at bounded terminal phases; dependency phase renewal pending |
| attempt counting / retry backoff | claimed-generation counting implemented; durable retry scheduling pending |
| stale-worker fencing | repository claim ownership is checked before checkpoint and terminal state writes |
| terminal applied/superseded/failed history | implemented for reconciliation outcomes |
| two-worker recovery / tenant isolation | unit coverage present; full Elasticsearch matrix pending |
| CLI execution / secret leakage | typed redacted output and documented exit codes implemented; hosted proof pending |

The next milestone is Data Product APIs, Product 360, browser/security, and final hosted core certification.

## Evidence status and mapping decision

Migrations `0001`–`0016` remain immutable. The existing generic document mapping is retained until the strict Elasticsearch writer/query suite proves that a `0017` mapping is necessary; no unproven mapping fields are added here. Plan/result persistence, state/history creation, CAS claiming, expiry/takeover, renewal, stale-worker fencing, checkpoints, bounded attempts, two-worker races, tenant isolation, CLI exit behavior, and leakage remain explicit certification controls. Hosted cells above intentionally remain pending until GitHub Actions artifacts exist.

Release readiness remains **blocked**. The next milestone is **Data Product APIs, Product 360, browser/security, and final hosted core certification**.
