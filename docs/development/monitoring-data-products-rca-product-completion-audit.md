# Monitoring, Data Products, and RCA product completion audit

This audit distinguishes foundations from completed product capabilities. Release readiness remains **blocked**. The Phase B hosted `certification_scope=all` result was not independently verifiable in this checkout, so this change does not claim Phase B closure or promote capabilities to validated.

| Capability | Existing code | Missing product/runtime surface | Implementation | Evidence |
|---|---|---|---|---|
| Monitor CRUD, revisions, ETags | Typed definitions and repository protocol | Full API and all repository operations | Lifecycle service, immutable event boundary, OCC Elasticsearch create/update | Focused unit tests |
| Schedules, leases, checkpoints | Deterministic scheduler and protocol | Complete production persistence/runtime | Not complete | None; blocker |
| Observations | Observer boundaries | Production append/history implementation | Not complete | None; blocker |
| Baselines | Robust statistical helpers | Immutable version persistence/reset workflow | Not complete | Existing unit evidence only |
| Evaluations and breach/recovery | Evaluator and recovery helpers | Durable projection and incident workflow | Not complete | Existing unit evidence only |
| Suppressions | Domain type/helper | Durable audited lifecycle | Not complete | None; blocker |
| Recommendations and coverage | Domain types/recommender foundations | Durable approval workflow and operational aggregation | Not complete | None; blocker |
| Monitors as Code | No complete product flow | Schema, plan/apply/export/drift and CLI | Not complete | None; blocker |
| Providers | Observer boundary | Provider implementations and orchestration | Bounded contract, registry and aggregate-only PostgreSQL expression compiler | Focused unit tests |
| Data Product CRUD/membership | Typed domain model | Production Elasticsearch workflow and reviewed proposals | Scoped repository/service foundations; in-memory test adapter | Focused unit tests only |
| SLO/reliability | Typed reliability model | Durable SLO evaluations and APIs | Evidence-honest observed-weight calculation | Focused unit tests |
| RCA persistence/collectors/hypotheses/progress | Domain and deterministic scoring foundations | Production repository, runtime and APIs | Not complete | Existing unit evidence only |
| APIs | Existing application routes | Monitor, product and RCA typed routers | Not complete | None; blocker |
| Console | Existing Console shell | Monitor Center, Product 360 and RCA Workbench | Not complete | None; blocker |
| Security | Existing threat model | Full implementation verification | PostgreSQL identifiers are validated; raw SQL is not accepted | Unit test; wider review blocked |
| Real-stack/browser/accessibility | Existing certification framework | Focused profile and hosted evidence | Not complete | None; release blocker |

## Migration decision

Migrations `0001` through `0012` remain unchanged. A `0013` migration is deliberately not introduced by this incremental change because the incomplete runtime does not yet justify provisioning all candidate state. Existing `0007` monitor, Data Product, and RCA resources must be reused; genuinely absent state should be added only alongside its production writer and real-Elasticsearch tests.

## Safety boundaries

The PostgreSQL compiler accepts reviewed aggregate operations and validated identifiers, never API/YAML SQL text. All production IDs are tenant/environment scoped, resource aliases are fixed constants, mutable definitions use Elasticsearch OCC plus ETags, and history uses create-only writes. No remediation or automatic recommendation acceptance is provided.
