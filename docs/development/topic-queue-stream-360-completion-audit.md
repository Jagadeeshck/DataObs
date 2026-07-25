# Topic, Queue, and Stream 360 completion audit

Audited from `main` at `65e549e` (the merge commit for PR #96). This document is deliberately evidence-led: presence
of a contract, calculation helper, or HTTP client is not treated as an executable vertical slice.

| Capability | PR #96 state | Blocking gap | Required correction | Test evidence |
|---|---|---|---|---|
| Kafka Observer | One-shot inventory service and process-local checkpoint | No durable scheduling, leases, or independent collection cadences | Durable Elasticsearch checkpoints/leases and bounded scheduler | Unit tests in this change; real stack pending |
| Inventory | Read-only Admin client foundation | Full scale and authorization scenarios unproven | Exercise cluster/topic/partition/group collection on three brokers | Pending container gate |
| Offsets and intelligence | Lag, drain-time, retention helpers | History was two-point and confidence fixed | Persist history and use robust bounded slope/rate methods | Unit tests; integration pending |
| Storage | `0009` projections | Observer checkpoint/lease resources absent | Forward-only `0010`; never edit `0001`–`0009` | Pending Elasticsearch 9.4.2 gate |
| Kafka Connect | Small REST and normalization boundary | Durable collector, changes, and approval verification incomplete | Complete safe collector/action lifecycle | Pending |
| Schema Registry | Small REST and compatibility boundary | Complete collection and semantic impact incomplete | Add typed collection, semantic rules, and evidence links | Pending |
| Product query API | No complete Stream 360 API | Required resources and actions unavailable | Add scoped Elasticsearch-backed routes and generated contracts | Pending |
| Console | No complete five-resource 360 experience | Routes, accessible heatmap, comparisons, and actions missing | Implement routes and real browser tests | Pending |
| Live updates | Existing shared SSE foundation | Stream events and replay/isolation unproven | Add scoped events and leakage tests | Pending |
| Integration environment | Kafka demo foundation only | No required three-broker Connect/Registry/OTel gate | Add deterministic container environment | Pending |
| Browser/accessibility | Not executed for PR #96 | No Playwright/axe evidence | Run browser container against real stack | Pending |
| CI evidence | No workflow run returned for PR #96 head | Completion cannot be claimed | Add blocking jobs and retain artifacts | Pending |
| Non-Kafka providers | Capability stubs | No production implementation | Continue to report unsupported | Contract tests |
| Job/Run dependency | PR #95 foundation | Not completion evidence | Treat as optional correlated evidence only | N/A |

The completion gate remains open until every pending entry has executable evidence. DataObs is not claimed to be
production-ready.
