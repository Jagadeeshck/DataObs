# Stream Intelligence production runtime v1 audit

## Preflight

The audited base is `ee8bb038a7349374cfef078cad7d7105786722a8`, the merge commit for PR #224. The checkout has no configured Git remote, so this commit is the latest locally auditable `main` state and hosted PR status cannot be independently queried. Merge-marker validation passed. The executable registry terminal is `0026_stream_anomaly_retention_intelligence`.

Migration 0026 was inspected without modification. Its five mutable indices, four data-stream contracts, strict mappings, and 90/180/365-day lifecycle retention are sufficient; no 0027 migration is warranted. Local static inspection confirms the aliases/contracts. Elasticsearch 9.4.2 execution is delegated to the opt-in real-stack workflow because Docker is unavailable in this execution environment.

PR #224 supplied dependency-free algorithms, capabilities, mappings, API discovery placeholders, and the initial Console page. It did not supply a historical repository, durable runtime/worker, detector CRUD, real projections, renewable leases, runtime health, or inventory pagination.

## Historical evidence source matrix

| Resource | Historical source | Resource key | Allowlisted evidence |
|---|---|---|---|
| Kafka cluster | `metrics-dataobs.kafka_cluster-*` | `cluster_id` | replication, offline partitions, throughput, availability, freshness |
| Topic | `metrics-dataobs.kafka_topic-*` | `topic_id` | production, partition throughput/size, derived message size, errors, retries, DLQ, replication, freshness |
| Consumer group | `metrics-dataobs.kafka_consumer_group-*` | `consumer_group_id` | lag, partition lag, offset progress, consume/drain rate, retention exhaustion, freshness |
| Connector | `metrics-dataobs.kafka_connector-*` | `connector_id` | failed/running tasks, restarts, throughput, backlog, error/retry, freshness |
| Pathway | `metrics-dataobs.pathway-*` | `pathway_id` | p95/p99, throughput, backlog, errors/retries/DLQ, reliability, availability, retention risk, coverage, freshness |

Queries are scope/resource/time filtered, date-histogram downsampled, sorted by bucket, capped at 5,000 points, timeout bounded, and field/index allowlisted. Empty buckets remain `missing`; measured zero remains numeric zero. Partial, stale, estimated, and inferred quality is retained.

## Acceptance matrix

| Requirement | Current state | Gap | Implementation |
|---|---|---|---|
| Detector persistence | Mapping only | No operations | Scoped CRUD and deterministic identity |
| Runtime execution | Algorithms only | No orchestration | Ordered fenced runtime |
| Historical evidence query | None | No series | Five resource-specific adapters |
| Anomaly projection | Mapping only | No writes | OCC current projection |
| Forecast projection | Mapping only | No writes | Append plus OCC repository operation |
| Failure candidate persistence | Mapping only | No writes | Metadata-only append plus OCC operation |
| Transition signals | Contract only | No emission | Deterministic transition-only signal |
| Checkpointing | None | Unsafe replay | OCC checkpoint after evidence/projection/signal |
| Lease renewal | Reliability pattern incomplete | Long-cycle loss | Fenced acquire/renew/release operations |
| Signed cursors | Codec existed | Not used here | Context-bound `search_after` pages |
| Runtime health | Placeholder | Fabricated status | Persisted scoped runtime state |
| Detector CRUD | Missing | No lifecycle API | Draft, ETag, If-Match, enable/disable/delete |
| Resource 360 integration | Links only | Rich panels pending | API contracts documented; panel expansion remains |
| Browser evidence | Initial page | Full scenarios pending | Workflow hook retained; hosted evidence required |
| Elasticsearch evidence | Migration contract | Local Docker unavailable | 9.4.2 service workflow and opt-in suite gate |

## Reliability and Team 3 audit

Reliability's scoped repository and `StaleWriter` fencing semantics were reused; its objective evaluator was not duplicated. Intelligence remains historical-deviation evidence and does not redefine an SLO. No stable documented Team 3 public intake callable was found in the audited tree, so no adapter was created. Signals stay in the Team 1 contract and never write Team 3 indices or trigger remediation.
