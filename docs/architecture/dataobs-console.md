# DataObs Console architecture

> DataObs Console is the guided product experience. Kibana remains the deep investigation and administration surface.

```mermaid
flowchart LR
  Browser[DataObs Console] -->|same-origin HTTPS; session cookie| API[DataObs API]
  API --> Query[Product query boundary]
  Query -->|tenant + environment predicates| ES[(Elasticsearch)]
  API -. safe allowlisted links .-> Kibana[Kibana investigation]
```

The browser never calls Elasticsearch or Kibana APIs and never persists production credentials. Command Center uses bounded server projections; Data Flow requests at most 1,000 nodes and 2,500 edges and distinguishes inferred evidence.

```mermaid
flowchart TB
  Sources[Assets / incidents / Kafka / pathways] --> Projection[Console summary projections]
  Projection --> Filter[Tenant + environment + time filter]
  Filter --> Summary[Command Center response + data_status]
```
