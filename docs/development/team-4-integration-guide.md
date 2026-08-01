# Team 4 integration development guide

Use the provider lifecycle and contracts in [Integration SDK v1](../architecture/integration-sdk-v1.md). Team 4 owns
provider-neutral collection and integrations except Kafka-family (Team 1) and Airflow/dbt/Spark (Team 2). Do not add
onboarding UI, deployment assets, shared workflows, or incident delivery from a provider change.

Provider pull requests must use synthetic fixtures, isolate optional dependencies, enumerate unsupported capabilities,
exercise tenant and credential boundaries, and preserve zero/missing semantics. Network destinations must be selected
by provider-owned validation rather than arbitrary configuration. Page size, concurrency, duration, retry attempts,
and emitted observations all require explicit bounds. Never place secrets, raw SQL, customer endpoints, or raw provider
exceptions in fixtures or evidence.

Certification follows `docs/development/certification-evidence-contract.md`. A local pass supports at most
`functional_unvalidated`; only successful exact-commit hosted and independently verified evidence supports promotion.
