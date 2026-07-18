# Six-pillar product model

```mermaid
flowchart LR
  platform[Platform Observability] --> api[DataObs Product APIs]
  pipeline[Data Pipeline and Job Observability] --> api
  data[Data Observability] --> api
  finops[FinOps and Cost Observability] --> api
  business[Business Observability] --> api
  ai[AI and Agent Observability] --> api
```

Canonical values are `platform`, `data_pipeline`, `data`, `finops_cost`, `business`, and `ai_agent`. Deprecated aliases are `full_stack -> platform` and `pipeline -> data_pipeline`.
