# DataObs product certification harness

The harness consolidates existing service entry points into profiles: `core`, `postgres`, `kafka`, `jobs`, `browser`, `security`, and `full`. Run `./scripts/certification/compose.sh config`, `up core|full`, `seed`, `test backend|browser|security`, `evidence`, and `down`.

> The certification environment proves only the capabilities and dimensions listed in its retained evidence manifest. It does not make DataObs as a whole production-ready.

```mermaid
flowchart TB
  core[core: Elastic, Kibana, API, Console, OTel, fixtures]
  postgres[postgres: PostgreSQL + scanner]
  kafka[kafka: 3 KRaft brokers + Connect + Registry + observer]
  jobs[jobs: deterministic adapter fixtures]
  browser[browser: Playwright + axe]
  security[security: denied/allowlisted fixtures]
  full[full] --> core & postgres & kafka & jobs & browser & security
  core --> public[certification-public]
  postgres & kafka --> data[certification-data]
  core & postgres & kafka & jobs --> control[certification-control]
  security --> denied[certification-denied]
```

```mermaid
flowchart LR
  F[Synthetic fixtures] --> I[Idempotent seed] --> P[Existing product surfaces] --> T[Bounded tests] --> R[Redact] --> M[Checksum manifest] --> H[Hosted artifact]
```

```mermaid
flowchart LR
  C[contracts] --> B[backend]
  C --> W[browser]
  C --> S[security]
  B & W & S --> E[summary/evidence]
```

```mermaid
flowchart LR
  E[Hosted evidence + run identity] --> V[Schema and required-group verification] --> P[Proposal only] --> H[Human review] --> L[Ledger update]
  Local[Local evidence] -->|cannot promote| X[blocked]
```

Fixtures contain no personal or real business data. Airflow/dbt/Spark fixtures prove parser/emitter contracts only; real providers are not certified. Connector credentials never enter API/Console/browser containers. Four sentinel classes are injected only at runtime, and any occurrence in retained output fails verification.
