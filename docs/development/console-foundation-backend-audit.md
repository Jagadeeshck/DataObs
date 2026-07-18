# Console foundation backend audit

Baseline: `main` at `1da3fea9694041561bd033a9a38a122e40b6e10b`, the merge commit for PR #87. The code and tests—not only the PR description—were reviewed.

| Concern | Current state | Required correction | Implementation | Test evidence |
|---|---|---|---|---|
| Released migration integrity | `0004` is present in the merged manifest and is treated as immutable. | Add all Console storage forward-only. | `0005_console_foundation` adds saved views, preferences and bounded summary projections without changing `0001`–`0004`. | Migration ordering/checksum unit test. |
| Shared trace isolation | PR #87 read the configured shared stream using only a time predicate, then assigned configured tenant context to every result. | Filter tenant, environment and optionally integration at source. | Pathway repository now applies mandatory tenant/environment predicates inside the PIT query. | Two-tenant repository query test. |
| Incremental paging | PR #87 closed its PIT after one page and persisted the PIT-specific `_shard_doc` cursor for a subsequent PIT. | Keep a PIT for the complete page sequence and checkpoint only a completed window. | The repository consumes every page from one PIT and deliberately does not persist its cursor. | Multipage test asserts one PIT and complete result set. |
| Checkpoint durability | Checkpoints were durable but unconditional. | Preserve window start and use compare-and-set. | Completed-window checkpointing is durable; full CAS remains a documented limitation for the next hardening pass. | Restart contract test is pending real Elasticsearch. |
| Kafka offset capability | Provider capability must not imply authoritative offsets without earliest/latest/committed timestamps and warnings. | Bind only complete providers and expose provenance. | Existing observer contracts were retained; Console treats unavailable projections as incomplete, never zero. | Existing Kafka observer unit suite. |
| Console reads | Kafka routes in PR #87 use `app.state.kafka_dsm`; incident manager is process-local. | Production Console routes must use Elasticsearch. | New `/command-center`, `/topology`, and entity summary boundaries accept only an Elasticsearch repository; memory mode returns dependency unavailable. | API OpenAPI and repository isolation tests. |
| Live updates | No Console event boundary. | Authenticated tenant/environment event stream with bounded replay. | SSE route establishes isolated, versioned keepalive framing and reconnect guidance. Durable replay is a known limitation. | Stream contract included in integration gate. |

## Review disposition

The cross-tenant trace relabelling and cross-PIT cursor defects are corrected in the query path. The process-local Kafka routes remain for backward compatibility and are **not used by the Console**. Authoritative offsets, full SSE replay/backpressure, and checkpoint compare-and-set require further integration work; therefore the pull request must remain draft and DataObs is not production-ready.
