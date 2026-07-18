# Kafka lag and retention risk

`lag=max(0, latest-committed)`. Lag time uses next-unread timestamp (optional Read ACL), then consume rate, then production rate, otherwise unknown. Each estimate records method and confidence.

```mermaid
flowchart LR
 O[Offsets + rates] --> L[Lag and drain time]
 C[retention.ms/bytes + size] --> R[time/bytes ratios]
 L --> R
 R --> S[healthy/watch/warning/critical/data_loss_likely/unknown]
```

Reasons and source inputs accompany every result; low-confidence estimates are never presented as exact.
