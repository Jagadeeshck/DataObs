# Lag, drain time, and retention risk

```mermaid
flowchart LR
 H[High watermark] --> L[Lag = max H-C, 0]
 C[Committed offset] --> L
 L --> D[Drain = lag / consume-produce]
 R[Delete retention] --> K[Retention risk]
 A[Oldest unconsumed age] --> K
```

Missing or stale offsets yield unknown/partial/stale values, never zero. Lag velocity uses time-ordered samples and exposes interval and count. Drain time is rounded to avoid false precision; a zero or negative net drain rate is `not_converging`. Delete-retention risk compares safely observed age to retention and checks whether committed offset precedes log start. Compact-only topics are `not_applicable` for this simplistic time deletion model. All results expose method, evidence, confidence, missing inputs, and whether evidence is measured, derived, or estimated.
