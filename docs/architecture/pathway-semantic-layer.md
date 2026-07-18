# Pathway semantic layer

```mermaid
flowchart LR
 S[Spans: current, legacy, Elastic APM] --> N[Normalize and protect keys]
 N --> T[Deterministic nodes and edges]
 T --> B[Time buckets and checkpoints]
 B --> M[edge/full/internal/partial projections]
```

Topology inferred without trace evidence is explicitly `inferred` or `partial_edge` with reduced confidence. Jobs and datasets require OpenLineage or explicit catalog evidence. Search-after checkpoints use timestamp plus document ID and permit a bounded late-event replay window.
