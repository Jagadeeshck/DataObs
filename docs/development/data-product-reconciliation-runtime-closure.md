# Data Product reconciliation runtime closure

> PR #131 implemented Elasticsearch operation-state and immutable-history persistence primitives only. This PR wires every scoped mutation to those primitives, implements operation-specific repair handlers, and certifies crash recovery and stale-worker fencing against Elasticsearch 9.4.2.

Release readiness remains **blocked**. Hosted artifact cells remain pending until the draft PR workflow produces downloadable evidence; local tests are not represented as hosted certification.

| Operation kind | Current mutation steps | Crash boundaries | Recovery handler | Memory proof | Elasticsearch proof | Hosted artifact |
|---|---|---|---|---|---|---|
| `manual_membership` | plan, projection, evidence, result | each durable write | durable-plan handler | unit recovery | integration scenario | pending hosted run |
| `proposal_accept` | plan, membership, transition, evidence, result | membership/transition/evidence | proposal decision handler | contract suite | integration scenario | pending hosted run |
| `proposal_reject` | plan, transition, evidence, result | transition/evidence | proposal decision handler | contract suite | integration scenario | pending hosted run |
| `proposal_expire` | plan, transition, evidence, result | transition/evidence | proposal decision handler | contract suite | integration scenario | pending hosted run |
| `proposal_supersede` | plan, transition, evidence, result | transition/evidence | proposal decision handler | contract suite | integration scenario | pending hosted run |
| `membership_exclude` | plan, exclusion, evidence, result | projection/evidence | durable-plan handler | contract suite | integration scenario | pending hosted run |
| `dependency_replace` | plan, token, upserts, tombstones, result | every edge boundary | durable dependency handler | dependency suite | integration scenario | pending hosted run |
| `product_lifecycle` | plan, revision, evidence, result | revision/evidence | lifecycle replay handler | service suite | integration scenario | pending hosted run |

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

The next milestone is Data Product APIs, Product 360, browser/security, and final hosted core certification.
