# Team 4 integration development guide

## Azure Data Platform v1

The Azure provider is explicitly registered as `azure` version `1` and reuses the Integration SDK and Collection Manager generic evidence/checkpoint stores. Install its lazy optional dependencies from `requirements-azure-data-platform.txt`; core and unrelated providers remain importable without them. Its closed configuration requires Azure Public Cloud, a tenant/subscription, and explicitly named ADF, Synapse, or ADLS resources. See the [architecture](../architecture/azure-data-platform-collector.md), [operations](../operations/azure-data-platform-collector.md), and [RBAC](../security/azure-data-platform-collector-rbac.md) guides.

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

The Snowflake warehouse collector v1 uses a lazy optional connector, closed authentication/configuration schemas, fixed bounded SQL templates, SQL-free query history, isolated evidence families and generic persist-before-checkpoint storage. Access History and canonical lineage require Team 2 review; packaging and UI onboarding remain Team 0 and Team 5 work. It remains `functional_unvalidated` until hosted exact-commit evidence is independently verified.

## Trino SQL engine v1

Trino is explicitly registered on the reusable Integration SDK SQL-engine foundation. Use only its fixed metadata/runtime registry and optional official Python client; never add custom SQL, JDBC, profiling, or business-row reads. Trino is `functional_unvalidated`.

## Presto SQL engine v1

PrestoDB is independently registered as `presto` and uses the same SQL-engine foundation without sharing Trino identity, authentication, headers, or dialect projections. Its optional official client, Basic-only authentication, fixed metadata/runtime SQL, and bounded-history semantics are documented in the Presto architecture, operations, and access guides. Presto is `functional_unvalidated` pending hosted exact-commit evidence.
