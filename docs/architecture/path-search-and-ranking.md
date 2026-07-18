# Path search and ranking

Path search operates only after tenant and environment isolation. It enumerates deterministic loopless paths with bounded hops, returned alternatives, and a hard work cap. Cycles are avoided by retaining the node IDs in each candidate.

```mermaid
flowchart LR
  R[Scoped request] --> F[Tenant/environment filter]
  F --> G[Evidence graph]
  G --> B[Bounded loopless traversal]
  B --> K[Deterministic rank]
  K --> O[Best, alternatives, partials and explanation]
```

Ranking is the documented mean of evidence confidence, completeness, recency, health, inverse path length, business relevance, active traffic and SLO coverage. Missing factors remain explicit; no AI model participates. Structural metadata is never promoted to pipeline lineage without independent evidence.
