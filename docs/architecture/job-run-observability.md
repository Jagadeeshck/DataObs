# Job and run observability

> OpenLineage provides the portable job and lineage event contract. Platform-native metadata provides deeper operational evidence. DataObs combines both without exposing source credentials or raw business data.

```mermaid
flowchart LR
 A[Airflow provider] --> I[Authenticated OpenLineage ingress]
 D[dbt artifacts/events] --> I
 S[Spark listener] --> I
 E[Spark replayable event log] --> O[Spark observer]
 I --> H[(Append-only evidence)] --> P[Job observer projections]
 O --> P --> M[Shared monitors] --> C[Incidents and explainable RCA]
 P --> API[Scoped bounded API] --> UI[Pipelines / Job 360 / Run Explorer]
 API --> K[Safe Kibana deep links]
```

Canonical identity includes tenant, environment, platform, namespace and name; source run IDs are integration-namespaced. Platform facets remain optional typed objects. Append-only evidence is never replaced by current-state projection. Raw SQL, rows, Kafka payloads, offsets, stack traces and credentials are excluded or reduced to redacted fingerprints/references.
