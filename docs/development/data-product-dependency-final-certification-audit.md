# Data Product dependency final-certification audit

PR #126 completed proposal/exclusion implementation scaffolding but did not provide real-stack hosted certification. This PR closes inherited recovery defects and completes the dependency vertical through OCC, traversal, reconciliation, API, Console, and retained evidence.

Release readiness remains **blocked**. Hosted evidence is intentionally not claimed by
this document; a workflow URL and retained downloadable manifest are required before
any capability is promoted. The next milestone is **Data Product SLOs, reliability,
and coverage**.

| Capability | Current main behavior | Blocking defect | Final behavior | Local evidence | Hosted evidence |
|---|---|---|---|---|---|
| manual membership pending recovery | Deterministic operation IDs | Pending evidence can outlive completion | Persisted pending evidence is reused | Membership recovery tests | Pending |
| proposal accept exact replay | Scoped idempotency exists | No hosted crash/retry proof | Immutable original result is replayed | Proposal decision tests | Pending |
| proposal accept membership consistency | Membership is projected | Cross-index interruption possible | Reconciler verifies projection and terminal evidence | Membership tests | Pending |
| proposal decision pending recovery | Pending decision is immutable | Timestamp regeneration may diverge | Read by deterministic decision ID and reuse | Recovery tests | Pending |
| proposal decision terminal recovery | Terminal evidence is append-only | Completion can be interrupted | Append only missing terminal evidence | Reconciliation tests | Pending |
| membership exclusion recovery | Projection and decision are separate | Partial state requires repair | Deterministic recovery compares both | Exclusion tests | Pending |
| proposal/exclusion real Elasticsearch evidence | Contract tests exist | No retained real-stack result | Elasticsearch workflow plus documents | Integration suite | Pending |
| proposal/exclusion real browser evidence | Components and focused specs exist | No hosted API/ES journey | Real-stack Playwright and axe | Browser specs | Pending |
| dependency complete-current read | First page only | More than 200 edges are omitted | Stable continuation is followed; hard cap fails closed | Dependency tests | Pending |
| dependency projection writes | Blind index | Lost updates possible | Create-only or sequence/primary-term OCC | Repository tests | Pending |
| dependency traversal | Tenant-wide 1,000-edge query | Large graphs silently omit evidence | Paginated frontier queries with explicit budgets | Frontier tests | Pending |

Migrations `0001`–`0016` are unchanged and migration `0016` is sufficient; no
speculative `0017` is introduced.
