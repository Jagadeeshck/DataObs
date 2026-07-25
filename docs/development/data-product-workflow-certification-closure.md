# Data Product workflow and certification closure audit

Base commit: `433edd9` (the local checkout contains the merge commit for PR #117). The checkout has no configured Git remote, so this audit cannot independently fetch GitHub or create hosted evidence. Migrations `0001`–`0015` are immutable; **no migration 0016 is required** by the lifecycle idempotency correction in this change.

> PR #117 added the typed product CRUD boundary and initial Console routes. It did not complete the Data Product workflows or certification gates until the concrete implementations and retained evidence in this PR exist.

The table is intentionally an evidence ledger rather than a claim of completion. `Blocked` entries must not be promoted in the capability ledger.

| Gap | Current code | Required implementation | Test | Hosted job | Evidence |
|---|---|---|---|---|---|
| Repository Protocol versus Elasticsearch implementation | Product CRUD/events/readiness only | Implement every Protocol operation | Contract + ES integration | data-product-contracts, data-product-elasticsearch | Blocked |
| Any-typed repository methods | Production Protocol uses `Any` | Bounded domain page/operation models | mypy + contract | data-product-contracts | Blocked |
| Product list filtering | API collects filters; repository ignores them | Scoped ES filters | integration/API | data-product-elasticsearch | Blocked |
| Signed cursor integration | Codec exists in isolation | Decode at API and pass sort values | cursor integration | data-product-security | Blocked |
| Next cursor generation | Hard-coded null | Over-fetch and sign final hit sort | pagination tests | data-product-contracts | Blocked |
| Lifecycle idempotency | Header was discarded | Route now propagates key through service operation identity | lifecycle propagation test | data-product-unit | Local |
| Revision listing | Protocol only | Typed scoped page | integration | data-product-elasticsearch | Blocked |
| Pending-operation reconciliation | Protocol only | Bounded OCC reconciler + telemetry | crash/concurrency | data-product-elasticsearch | Blocked |
| Manual membership | Models only | Service, repository, API and UI | unit/integration/browser | data-product-browser | Blocked |
| Proposal generation | Models only | Evidence-bounded generation | poisoning/security | data-product-security | Blocked |
| Proposal decisions | Models only | Create-only decisions and idempotency | concurrency | data-product-elasticsearch | Blocked |
| Membership exclusion | Absent | OCC exclusion projection | integration | data-product-elasticsearch | Blocked |
| Dependency persistence | Product-embedded compatibility data | Current projection + event | strict mapping/integration | data-product-elasticsearch | Blocked |
| Dependency traversal | Create/update validation only | Bounded directional graph | property/security | data-product-security | Blocked |
| SLO persistence | Models/evaluator foundation | OCC definition writers | integration | data-product-elasticsearch | Blocked |
| SLO revision lifecycle | Absent | Immutable revisions/actions | lifecycle tests | data-product-elasticsearch | Blocked |
| SLO evaluation persistence | Evaluation model only | Immutable corrected-evidence identity | integration | data-product-elasticsearch | Blocked |
| Reliability current/history | Model only | OCC current + immutable events | formula/replay | data-product-unit | Blocked |
| Coverage | Model only | Evidence-backed dimensions | unit/integration | data-product-unit | Blocked |
| Incident summary | Model only | Scoped bounded metadata query | integration/security | data-product-security | Blocked |
| Change summary | Model only | Scoped bounded metadata query | integration/security | data-product-security | Blocked |
| Impact | Model only | Persisted bounded projection | graph/integration | data-product-elasticsearch | Blocked |
| API routes | CRUD/lifecycle only | Add workflow routes | OpenAPI/API | data-product-contracts | Blocked |
| Product list actions | Initial list only | Evidence values/actions/states | browser | data-product-browser | Blocked |
| Product 360 tabs | Overview/Outputs foundation | API-backed workflows | Playwright | data-product-browser | Blocked |
| Browser | Not retained | Full list/tab workflow | Playwright | data-product-browser | Blocked |
| axe | Not retained | Serious/critical-free scans | axe | data-product-browser | Blocked |
| Security | Incomplete | Scope, cursor, graph, poisoning, XSS gates | security suite | data-product-security | Blocked |
| Elasticsearch | No retained 9.4.2 run | Real-stack integration | integration | data-product-elasticsearch | Blocked |
| Hosted CI | No run URL/artifact manifest | Required jobs and retained hashes | summary validation | data-product-summary | Blocked |

## Release decision

Release readiness remains **blocked**. Capability claims must remain unchanged until local real-stack, browser, accessibility, security, upgrade, and hosted evidence exists. Durable explainable RCA is the next milestone only after every blocked row above is closed.
