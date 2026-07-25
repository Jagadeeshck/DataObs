# Critical path and bottlenecks

```mermaid
flowchart LR
 G[Dependency and timing graph] --> V[Validate DAG]
 V --> L[Longest elapsed path]
 L --> S[Segments: wait, execution, slack]
 S --> B[Separate bottleneck methods]
```
The implementation uses actual dependency edges and elapsed durations. Cycles/missing nodes lower confidence and set an incomplete-graph warning. Orchestration delay, execution duration, volume, saturation, shuffle/spill, skew, retry, source wait, backlog, and infrastructure failure remain separate analyses; unrelated units are never collapsed into a score.
