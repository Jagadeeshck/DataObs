# Topic, Queue, and Stream 360 foundation audit

PR #95 is merge commit `1a837e8`; it added a job/run foundation whose OpenLineage repository remains in-memory. Stream responses therefore must report job/run linkage as `partial` or `not_configured` until durable evidence is present. The latest pre-change migration was `0008_job_run_observability`; migrations 0001–0008 were not edited.

| Concern | Current implementation | Gap | Required action | Test evidence |
|---|---|---|---|---|
| Kafka cluster/topic inventory | Read-only Confluent Admin inventory and 0004 Kafka projections | Collection was monolithic and Kafka-specific | Retain adapter and add provider-neutral projections/budgets | Kafka integration required before draft promotion |
| Complete offset inventory | Consumer exists but offset enumeration was absent | Earliest, high watermark, stable and committed offsets incomplete | Bounded partition/group batches and honest partial results | Unit offset math; real Kafka pending |
| Offset semantics | Existing lag helper used latest/committed | No stale/out-of-range representation | Typed offset samples return partial/stale rather than zero | `tests/stream_360` |
| Partition leader/replica/ISR | Admin inventory captures leader, replicas and ISR | No explainable classification | Derive offline/under-replicated with method/confidence | `tests/stream_360` |
| Topic configuration redaction | Existing allowlist and recursive redaction | Secret-like native values still require regression coverage | Drop non-allowlisted keys before persistence | sentinel unit test |
| Group members/assignments | Admin descriptions capture members/assignments | Generation, rebalance history and paging incomplete | Add bounded group polling and append-only rebalance events | real Kafka pending |
| Rebalance evidence | No durable event stream | Snapshot cannot prove churn/duration | 0009 adds rebalance stream; observer projection remains follow-up | pending integration |
| Producer/consumer identity | Pathway OTel normalization exists | Correlations require explicit evidence/confidence | Provider-neutral application contracts | contract tests |
| OTel messaging traces | Existing pathway semantic layer | Trace coverage can be absent | Reuse traces; never copy payloads; return partial | pathway tests |
| Pathway projections | 0004 and pathway worker exist | Stream 360 query composition incomplete | Reuse the graph model | existing pathway suite |
| Schema Registry | Kafka schema models only | No client/structural compatibility rules | Safe Confluent-compatible boundary and rules | schema unit test |
| Kafka Connect | Connector models only | No safe client/redaction boundary | Allowlisted HTTPS/read-only client; approved restart only | redaction unit test |
| Alert/monitor lifecycle | Shared 0007 monitoring runtime | Stream observation bindings incomplete | Use shared monitor engine, never a Kafka-only engine | existing monitor suite |
| Incident/RCA linkage | Stream failure hypotheses exist | Contradicting evidence depends on telemetry | Preserve explainable hypotheses and insufficient evidence | existing RCA suite |
| Console routes | Console/pathway routes exist | Stream 360 screens are not complete | Add screens only after backed APIs | browser validation pending |
| SSE | Console live-update foundation exists | Stream events not fully projected | Tenant-scoped typed events with bounded replay | pending browser stack |
| Migration immutability | Checksummed forward migrations | 0009 absent before this milestone | Append 0009 only | migration unit test |
| Real containers | Existing integration Compose is not three-broker Stream demo | Definition-of-done unmet | Run Elasticsearch 9.4.2 + 3 broker KRaft stack | pending environment |
| GitHub Actions | General Python/Console jobs exist | Dedicated blocking Stream jobs absent | Add only when reproducible stack exists | pending CI |

This audit deliberately does **not** claim a completed Kafka vertical slice or production readiness.
