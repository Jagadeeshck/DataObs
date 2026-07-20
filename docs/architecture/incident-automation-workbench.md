# Incident and Automation Workbench

> DataObs owns incident intelligence, policy, approvals, verification and the operator experience. Elastic Cases owns collaborative Case records and external Case synchronization. Elastic Workflows owns declarative runbook execution when available. DataObs does not duplicate a generic workflow engine.

```mermaid
flowchart LR
  F[Versioned findings] --> C[Explainable correlation]
  C --> I[Durable incident and timeline]
  I --> K[Elastic Case]
  I --> W[Elastic Workflow recommendation]
  W --> P[Policy and human approval]
  P --> A[Allowlisted adapter]
  A --> V[Measured verification]
  V -->|verified| R[Human resolution and review]
  V -->|failed or inconclusive| I
```

Provider success and measured recovery are separate states. Resolved and closed are separate human-controlled lifecycle states. Recommendations never auto-start and capability failures are represented honestly.
