# Monitoring, Data Products, and RCA product completion audit

This audit distinguishes foundations from completed product capabilities. Release readiness remains **blocked**. The Phase B hosted `certification_scope=all` result was not independently verifiable in this checkout, so this change does not claim Phase B closure or promote capabilities to validated.

| Capability | PR #112 implementation | Remaining gap | Implementation in this PR | Evidence |
|---|---|---|---|---|
| Monitor lifecycle | Typed definitions, lifecycle service, ETags and a partial protocol | Typed API and production runtime remain absent | Unified authoritative protocol; immutable intent is written before mutable state | Focused unit tests |
| Schedules, leases and checkpoints | Deterministic scheduler and partial protocol | Production persistence/runtime | Contract reconciled only; not complete | None; blocker |
| Observations | Observer boundaries | Production append/history implementation | Not complete | None; blocker |
| Baselines | Robust statistical helpers | Immutable version persistence/reset workflow | Not complete | Existing unit evidence only |
| Evaluations and breach/recovery | Evaluator and recovery helpers | Durable projection and incident workflow | Not complete | Existing unit evidence only |
| Suppressions | Domain type/helper | Durable audited lifecycle | Not complete | None; blocker |
| Recommendations and coverage | Domain types/recommender foundations | Durable approval workflow and operational aggregation | Not complete | None; blocker |
| Monitors as Code | No complete product flow | Schema, plan/apply/export/drift and CLI | Not complete | None; blocker |
| Providers | Observer boundary | Provider implementations and orchestration | Bounded contract, registry and aggregate-only PostgreSQL expression compiler | Focused unit tests |
| Data Product persistence and revisions | Typed domain model, service, and in-memory adapter | Production Elasticsearch workflow and reviewed proposals | Authoritative revision, revision-aware ETag, actor/reason event, divergent replay rejection | Focused unit tests only |
| Dependencies, cycles, SLO and reliability | Typed reliability model and immediate dependency check | Durable SLO evaluations and APIs | Create/update validation now performs bounded deterministic recursive traversal | Focused unit tests |
| RCA persistence/collectors/hypotheses/progress | Domain and deterministic scoring foundations | Production repository, runtime and APIs | Not complete | Existing unit evidence only |
| APIs | Existing application routes | Monitor, product and RCA typed routers | Not complete | None; blocker |
| Console | Existing Console shell | Monitor Center, Product 360 and RCA Workbench | Not complete | None; blocker |
| Security | Existing threat model | Full implementation verification | PostgreSQL identifiers are validated; raw SQL is not accepted | Unit test; wider review blocked |
| Real-stack/browser/accessibility | Existing certification framework | Focused profile and hosted evidence | Not complete | None; release blocker |

## Migration decision

Migrations `0001` through `0012` remain unchanged. A `0013` migration is deliberately not introduced by this incremental change because the incomplete runtime does not yet justify provisioning all candidate state. Existing `0007` monitor, Data Product, and RCA resources must be reused; genuinely absent state should be added only alongside its production writer and real-Elasticsearch tests.

## Safety boundaries

The PostgreSQL compiler accepts reviewed aggregate operations and validated identifiers, never API/YAML SQL text. All production IDs are tenant/environment scoped, resource aliases are fixed constants, mutable definitions use Elasticsearch OCC plus ETags, and history uses create-only writes. No remediation or automatic recommendation acceptance is provided.


## Foundation consistency correction in this change

Definition events are written create-only **before** the mutable monitor document. This does not claim a cross-index transaction. A crash can leave an unapplied immutable intent, which is visible and safe to replay; current-state mutation can no longer succeed and then silently lose its history. Exact event replays compare the full scope, revision, ETag, action, and canonical definition checksum. A conflicting payload raises a consistency error. A reconciliation worker and applied marker remain a blocker before this strategy is operationally complete.

## Completion status

This change corrects a bounded set of PR #112 foundation defects. Migration `0013`, runtime writers, production repositories, APIs, Console surfaces, real Elasticsearch/provider/browser/accessibility/security certification, and hosted evidence remain absent. Therefore this audit remains intentionally non-promotional and release readiness remains **blocked**.
