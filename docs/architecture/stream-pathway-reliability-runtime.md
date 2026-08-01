# Stream and pathway reliability runtime v1

Status: `functional_unvalidated`. Team 1 owns the pure evaluator and the Kafka/pathway workers; it does not use Team 2's monitor runtime.

## Capability matrix

| Resource | Metrics backed by current projections |
|---|---|
| Kafka cluster | under-replicated partitions, offline partitions, observation freshness |
| Topic | producer throughput floor, under-replicated partitions, offline partitions, observation freshness |
| Consumer group | consumer lag, maximum partition lag, lag growth rate, estimated drain time, consumer throughput floor, retention risk, suspected data loss, observation freshness |
| Connector | failed tasks, running-task ratio, observation freshness |
| Pathway | latency p95/p99, reliability, availability, backlog, retention risk, observation freshness, source coverage |

The registry is fail-closed: a metric/resource pair not listed is rejected. Evidence precedence is trace-derived evidence, bounded projection evidence, then unavailable. `edge_estimate` remains explicitly estimated; `unavailable` is never measured latency. Measured zero is a value. Missing evidence remains `null` and never becomes zero or healthy.

## Evaluation and state

An enabled, due definition is evaluated over a maximum 31-day bounded window. Operators are `gt`, `gte`, `lt`, and `lte`. Breaches first enter `warning`, then `breaching` after the configured count. A confirmed breach enters `recovering` after a non-breach and becomes `healthy` only after the recovery count. Projection counters and first-breach time make restart behavior deterministic. Missing policy defaults to `no_data`; alternatives are `breach` and `ignore`. Stale evidence is always `stale`.

Evaluation IDs hash tenant, environment, definition, revision, and UTC window end. A tenant/environment lease carries a fencing token. The append-only evaluation is persisted before its checkpoint. Confirmed breaches yield redaction-safe Team 1 signals; consumers may translate the public signal but this runtime neither writes Team 3 private indexes nor remediates.

## Storage

Migration `0023_stream_pathway_reliability_runtime` adds versioned definitions, current status and coordination indices, plus evaluation and signal data streams. Fixed read/write aliases are created by the shared migrator. All documents are tenant/environment scoped. Rollback stops workers first, retains evidence, snapshots current status, and only then removes 0023 resources after review.

## Limitations

Correlation is evidence, not root cause. No remediation is attempted. Runtime effectiveness is not certified until exact-commit hosted evidence is retained.
