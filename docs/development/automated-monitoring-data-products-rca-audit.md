# Automated monitoring, Data Products, and RCA audit

Latest available `main` at branch creation was `12322a3`; the local history records PR #92 as merged by that commit. This checkout had no Git remote configured, so remote freshness could not be independently fetched.

| Capability | Current state | Gap | Implementation plan | Test evidence |
|---|---|---|---|---|
| Monitor contract | `Monitor` was a small stringly typed entity | No stable types, revision, ETag, baseline explanation, or finding contract | Versioned Pydantic definitions, enums, observations, evaluations, findings, suppression, recommendation, coverage, tuning, and audit models | `tests/automated_monitoring/test_vertical_slice.py` |
| Freshness and distribution | PostgreSQL freshness and quality drift existed as separate paths | No shared baseline lifecycle | Deterministic robust baseline and evaluation contract; adapters remain follow-up work | Robust baseline/outlier tests |
| Pathways | Kafka measurements and pathway monitor state exist | Evaluation lifecycle was not unified | Shared monitor types cover latency, lag, retention, throughput, error and DLQ rates | Domain validation and migration coverage |
| Storage | Migrations 0001–0006 establish strict indices and streams | No durable versioned monitor/Data Product/RCA state | Forward-only 0007 with aliases, strict mappings, streams, and executable latest transforms | Migration manifest test; real ES remains required |
| Recommendations | No general recommender | No evidence/cost/approval contract | Transparent heuristic boundary and human-approved recommendation model | Coverage and heuristic unit coverage |
| Coverage | Counts and view summaries only | Counts do not express health, maturity, or gaps | Category-aware coverage states, numerator/denominator, gaps and recommendations | Partial-coverage test |
| Data Products | Not first-class | No durable membership or reliability formula | Typed products, evidence-backed members, SLOs and weighted observed-only score | Missing-evidence reliability test |
| RCA | Incident correlation and pathway investigation exist | No ranked hypothesis engine | Deterministic weighted factors with supporting, contradicting and missing evidence; ranking never confirms | Deterministic contradiction test |
| Browser/real stack | Prior audits record validation unavailable | No defensible browser or PostgreSQL/Kafka/ES 9.4.2 evidence | Keep PR draft until container integration, Playwright and axe pass | Not executed in this environment |
| Migration immutability | 0001–0006 checksums are history-sensitive | Editing them breaks upgrades | Append 0007 only; retain `dataobs-monitors-v1` | Manifest regression test |

This slice is intentionally not represented as production-ready. API persistence, complete schedulers, Console routes, real-stack validation, alert/workflow packs, and all operational adapters remain required before release.

> DataObs must never claim certainty where evidence is incomplete. Monitor evaluations, data-product reliability and RCA hypotheses must expose their data coverage, method and confidence.
