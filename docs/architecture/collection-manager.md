# Collection Manager

```mermaid
sequenceDiagram
  participant API
  participant CM as Collection Manager
  participant S as Scanner
  API->>CM: Register source/scanner/scan policy
  S->>CM: Heartbeat
  S->>CM: GET tasks
  S->>CM: ACK task
  S->>CM: Submit synthetic schema snapshot
  CM->>CM: Append event and update asset current state
```

The initial control plane supports tenant-aware source, integration, collector, scanner, heartbeat, scan-policy, task, acknowledgement, and idempotent result APIs. Fleet and EDOT adapters intentionally return `not_implemented`.
