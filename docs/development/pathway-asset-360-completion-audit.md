# Pathway Explorer and Asset 360 completion audit

Baseline: `d87ef89` (merge of PR #91). This audit describes the inspected implementation, not the PR description. The completion work remains a bounded product slice and is **not** a production-readiness claim.

| Capability | PR #91 state | Production gap | Required correction | Test evidence |
|---|---|---|---|---|
| Pathway Explorer API execution | API existed; Console only changed URL state | No browser request or cancellation | Execute the tenant/environment-scoped API with an abort signal | TypeScript build and browser integration gate |
| Graph rendering | Empty placeholder | No route representation | Render selected route and retain an accessible route table | Component and axe/browser gate |
| Alternative path selection | API returned alternatives | UI did not expose selection | Combine ranked complete/partial routes and update every selected-route panel locally | Component/browser gate |
| Latency and bottlenecks | Typed summaries were partial | No durable metric projection/query implementation | Keep unavailable values explicit; implement aggregation projections before declaring complete | Blocked: real-stack metric fixtures required |
| Time comparison | Contract only | No endpoint/UI | Add current/baseline aggregation endpoint and correlated-change panels | Blocked: real-stack comparison fixture required |
| Monitor creation | Disabled button; migration 0006 contained monitor index | No CRUD/evaluation lifecycle | Keep action disabled until review/confirmation workflow and durable incident integration exist | Blocked: monitor integration test required |
| Catalog cursor pagination and filters | Returned an ID cursor that was ignored | Repeated first page; minimal filtering | Versioned opaque search-after cursor, deterministic sort and allowlisted filters; URL state and paging controls | Unit/API and 100k fixture gate |
| Asset 360 sections | Six projections plus hard-coded cost | Required sections absent | Allowlist all required sections and honestly return `not_configured` when a projection is absent | API/component tests |
| Raw JSON rendering | Main tab body was a JSON `pre` | Not task-oriented or accessible | Typed fact panels, evidence cards and empty/not-configured explanations; no raw JSON main view | Component/axe test |
| Elasticsearch persistence | Console repository backed the principal reads | pathway API downloaded up to 1,000/2,500 topology records | Replace with adjacency/route projection queries before production-scale approval | Blocked: Elasticsearch 9.4.2 scale test |
| Migration `0006` | Present and forward-only after 0005 | Missing completion projections may require 0007 | Do not alter 0001–0006; add 0007 only alongside proven storage requirements | Existing migration tests; real upgrade gate pending |
| Tenant/environment isolation | Repository predicates on principal tenant and requested environment | Must be exercised across every new index and cursor | Preserve predicates and add two-tenant/multi-environment real-stack assertions | Integration gate |
| SSE | Tenant/environment keepalive with Last-Event-ID echo | No replay/event source or targeted invalidation | Durable bounded replay and scoped event filtering required | Blocked: live integration gate |
| Kibana links | UI deliberately disabled | No server allowlist/link builder | Remain disabled until safe server-generated targets are implemented | Unsafe URL negative test required |
| Playwright | Test dependency present | PR #91 had no successful browser evidence | Run in pinned Playwright container against real API/Elasticsearch | Pending CI/container evidence |
| Accessibility | Semantic shell and initial labels | Graph alternative and automated axe evidence absent | Accessible route table, live status, focus visibility and reduced motion; run axe | Pending axe evidence |
| Container integration | Console demo only | No completion compose stack | Add and validate the requested pinned multi-service stack | Pending container evidence |
| Workflow-run evidence | No run returned for PR #91 head | Completion cannot be labelled validated | Attach URLs/artifacts only after actual successful jobs | Pending human-review PR checks |

## Gate conclusion

The baseline was a scaffold. This change removes the two most visible placeholders and repairs catalog cursor semantics, but the rows explicitly marked **Blocked** remain completion blockers. The draft PR must remain draft until the real Elasticsearch, PostgreSQL, Kafka, OpenTelemetry/OpenLineage, Playwright and axe paths produce evidence.

> Pathway Explorer explains how data travels, where delay or failure accumulates, and what is affected. Asset 360 explains the complete observed state of one asset. Kibana remains the deep investigation surface.
