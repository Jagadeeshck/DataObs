# Console live updates

```mermaid
sequenceDiagram
 Console->>API: GET /events/stream + Last-Event-ID
 API->>API: authenticate + tenant/environment scope
 API-->>Console: versioned event / keepalive / retry
 Console->>Console: invalidate only affected query keys
```

The foundation supplies versioned keepalive and reconnect framing. Durable bounded event replay and backpressure metrics are intentionally called out as incomplete and keep the PR in draft.
