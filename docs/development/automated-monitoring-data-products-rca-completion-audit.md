# Automated monitoring, Data Products, and RCA completion audit

Baseline audited: `e9604f36ea4cc9f47f2c5c67886b3a1b0772c309` (merge of PR #93). This is a
completion audit, not a production-readiness assertion. A name or boundary module
is not counted as an implementation.

| Capability | PR #93 implementation | Blocking gap | Required correction | Test evidence |
|---|---|---|---|---|
| Monitor runtime | Domain models, robust statistics, and a breach predicate | CLI and durable scheduler/repository implementations were absent | Added durable repository protocol, bounded deterministic schedule planning, and explainable evaluation decisions; Elasticsearch adapter and service process remain required | `tests/automated_monitoring/test_runtime_completion.py` |
| Observation providers | Existing freshness, quality, Kafka, and pathway projections | PostgreSQL aggregate provider and provider orchestration remain absent | Implement read-only, budgeted aggregate providers and container-backed validation | Not run; blocking |
| Baselines | In-process statistical helpers | Persisted immutable baseline versions and reset audit remain absent | Add `0008`, history repository, immutable versions, and upgrade tests | Existing vertical-slice unit tests only; blocking |
| Recommendations | Heuristics and coverage calculation | Lifecycle/service was a boundary | Added deterministic generation, duplicate filtering, lifecycle validation, and approval callback; durable persistence remains required | `tests/automated_monitoring/test_runtime_completion.py` |
| Monitoring coverage | Category-aware calculation | Operational recency, source health, and durable projections incomplete | Project current operational coverage in Elasticsearch | Existing vertical-slice unit test only; blocking |
| Data Products | Domain models and reliability function | Durable CRUD, membership discovery, SLO service and API remain absent | Implement tenant-scoped repositories and reviewable traversal | Not run; blocking |
| RCA | Hypothesis model and deterministic factor weights | Investigation orchestration was a boundary | Added tenant-filtered structured-evidence orchestration with explicit contradictions; durable progress, collectors and API remain required | `tests/automated_monitoring/test_runtime_completion.py` |
| Incident/Case/workflow | Existing incident automation primitives | Completion workflow packs and end-to-end recovery linkage remain absent | Add safe packs and monitor-to-incident-to-RCA integration | Not run; blocking |
| Monitors as Code | Domain fields only | Validate/plan/apply/export/drift are absent | Implement schema, compiler, state repository, and CLI | Not run; blocking |
| API | Existing product query routes | Requested monitor/product/RCA route sets are incomplete | Add typed scoped routes, ETags, pagination, and regenerate OpenAPI | Not run; blocking |
| Console | Existing Command Center, Asset 360, and Pathway screens | Monitor Center, Data Product 360, and RCA Workbench are absent | Build browser-tested screens against the real API | Not run; blocking |
| Elasticsearch migration | `0007` resource declarations | No forward-only executable `0008` or Elasticsearch 9.4.2 upgrade evidence | Add complete strict mappings/transforms without modifying `0001`–`0007` | Not run; blocking |
| Real-stack validation | No returned workflow run for PR #93 head | PostgreSQL, Kafka, Elasticsearch, Playwright/axe, and leakage scans did not run | Run the completion compose stack and all blocking CI jobs | Not run; blocking |

## Gate status

The completion gate remains **open**. This repository must not be described as
production-ready, and no autonomous or destructive remediation is enabled.
Monitor evaluations, Data Product reliability and RCA hypotheses must expose
method, evidence, missing coverage and confidence. DataObs must never represent
absent evidence as health or certainty.
