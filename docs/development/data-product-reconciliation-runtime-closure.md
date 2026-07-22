# Data Product reconciliation runtime closure

> PR #138 fixed proposal field access, legacy-worker comparison and idempotency binding only. It did not wire mutation services to the shared coordinator, complete dependency/lifecycle repair, implement the real Elasticsearch/security fault matrix, or produce hosted evidence. This PR closes the runtime and certification gate.

> PR #137 added claim-fenced handler mechanics and partial proposal/exclusion repair, but mutation services were not wired to the coordinator, dependency and lifecycle recovery remained incomplete, two P1 defects were introduced, and real Elasticsearch/security/hosted certification remained absent. This PR closes the reconciliation runtime and evidence gate.

> PR #136 added an authoritative service, terminal idempotency contracts and coordinator scaffolding only. The mutation services and concrete handlers still did not apply most missing projections, normal success paths still left generic state pending, and real Elasticsearch/security/hosted certification remained absent. This PR implements and proves the repair runtime.

> PR #135 closed terminal-status replay, result reuse, query filtering, and initial Elasticsearch completion-repair defects only. Proposal, exclusion, dependency and lifecycle handlers still did not perform missing mutations; normal success paths still left generic state pending; terminal-state repair, full fault testing, security evidence, hosted artifacts, and review-thread closure remained incomplete. This PR closes the reconciliation runtime.

> PR #134 added typed results, limited renewal, manual membership creation and partial plan wiring, but proposal, exclusion, dependency and lifecycle handlers still did not apply missing projection steps; synchronous workflows left generic state incomplete; terminal replay/history contained P1 defects; production idempotency repair and hosted Elasticsearch evidence remained absent. This PR closes those blockers.

> PR #131 implemented Elasticsearch operation-state and immutable-history persistence primitives only. This PR wires every scoped mutation to those primitives, implements operation-specific repair handlers, and certifies crash recovery and stale-worker fencing against Elasticsearch 9.4.2.

> PR #132 introduced generic reconciliation envelopes and dispatch scaffolding, but all operation kinds still used one non-repairing DurablePlanHandler and mutation services did not create the new operation state. This PR implements concrete projection-aware handlers and wires every scoped mutation into the runtime.

> PR #133 introduced named projection-aware handlers and partial mutation bootstrapping, but missing projection steps still returned retry rather than being repaired; proposal and exclusion workflows were not wired; synchronous paths left generic state incomplete; and real Elasticsearch fault certification remained absent. This PR closes those runtime gaps.

Release readiness remains **blocked**. Hosted artifact cells remain pending until the draft PR workflow produces downloadable evidence; local tests are not represented as hosted certification.

| Capability | Current main defect | Required behaviour | Unit/property | Elasticsearch 9.4.2 | Security | Hosted artifact |
|---|---|---|---|---|---|---|
| terminal outcome replay | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| terminal-state repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| canonical applied history | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| canonical failed history | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| canonical superseded history | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| immutable result reuse | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| idempotency completed repair | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| idempotency failed repair | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| idempotency superseded repair | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| pending idempotency operation binding | rejected an unbound reservation | bind `None` only after fingerprint and scope validation | covered | pending | pending | pending |
| full canonical terminal comparison | compared outcome and checksums only | compare every deterministic terminal semantic field | covered | pending | pending | pending |
| handler context usage | handlers received a raw ignored claim | claim assertion, renewal, and phase checkpoint API | covered | pending | pending | pending |
| manual projection repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| manual business terminal repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal accept repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal reject repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal expire repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal supersede repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| membership exclusion repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency product token | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency upserts | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency tombstones | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency complete immutable result | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency >200 upstream result | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| dependency claim renewal | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| lifecycle pre-transition plan/state | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| lifecycle transition repair | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| synchronous generic result/history/state | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| pending retry delegation | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| authoritative reconciler | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| retry scheduling | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| attempt exhaustion | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| two-worker takeover | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| stale-worker fencing | PR #135 partial baseline | operation-specific, claim-fenced repair | covered | pending | pending | pending |
| real Elasticsearch matrix | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| real security matrix | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| hosted manifest | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| review threads | PR #135 partial baseline | operation-specific, claim-fenced repair | pending | pending | pending | pending |
| proposal non-accept result construction | read nonexistent proposal `revision` / `etag` | typed proposal revision/state and canonical result checksum | covered | pending | pending | pending |
| legacy worker identity compatibility | worker delivery id participated in business equality | ignore worker id while preserving immutable legacy event | covered | pending | pending | pending |
| idempotency scope/action/fingerprint binding | repair checked only fingerprint and operation id | OCC bind/verify tenant, environment, product, action, fingerprint, operation | covered | pending | partial | pending |
| dependency >1,000 edge completeness | one bounded page can truncate evidence | verify complete durable snapshot | pending | pending | pending | pending |
| state/history/plan/result discrimination | envelope post-filtering can starve results | discriminate in Elasticsearch before size/limit | partial | pending | pending | pending |
| hosted manifest and review-thread closure | no retained hosted proof | resolve only from successful retained workflow evidence | n/a | pending | pending | pending |
| deterministic proposal result | recovery sampled a new clock value | derive `applied_at` from immutable pending decision evidence | covered | pending | pending | pending |
| proposal terminal revisit decoding | replay assumed generic revision/ETag fields | decode by operation kind and bind non-accept decisions to the result checksum | covered | pending | pending | pending |

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
| canonical actor / worker policy | actor and reason are durable plan fields and must match; ephemeral worker identity is redacted from canonical terminal history |
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

## Recoverable coordinator implementation gate

The synchronous manual-membership, proposal-decision, membership-exclusion,
dependency-replacement, and lifecycle entry points now create generic durable
state through `RecoverableDataProductOperationCoordinator` and delegate generic
completion to `DataProductOperationService`. Projection success is no longer
considered completion: immutable results and terminal history precede repaired
idempotency and applied state.

Lifecycle plans contain the complete target product and are persisted before
the OCC update; the lifecycle handler can apply that target when the source
revision and ETag still match. Dependency results are read from a complete
snapshot and every planned upsert/tombstone is checksum-verified, avoiding a
single-page result cap. Retryable reconciliation releases its claim into a
persisted, due-time-filtered retry schedule, and non-accept proposal replay uses
the durable UTC `payload.applied_at` rather than envelope persistence time.

This remains an implementation-only gate. Release readiness is **blocked** and
the next gate is **real Elasticsearch 9.4.2 reconciliation, security, and hosted
artifact certification**; no Product 360, Impact, SLO, reliability, coverage,
RCA, or production-readiness capability is promoted here.
