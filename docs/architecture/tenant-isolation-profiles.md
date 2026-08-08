# Tenant isolation profiles

## Implemented and testable: `shared`

| Boundary | Contract |
|---|---|
| Kubernetes | Shared installation and namespace; no physical isolation claim |
| Elasticsearch | Shared external cluster; every query and document is tenant/environment filtered |
| Network | Installation NetworkPolicies; not tenant-specific network separation |
| IAM | External identity plus durable tenant/environment-scoped DataObs bindings |
| Secret | References only; no tenant may read another tenant's references or values |
| Telemetry | Tenant identifiers belong in protected logs/traces, never metric labels |
| Backup | Shared repository with deterministic tenant resource inventory |
| Capacity | Safety quota profile and installation capacity guardrails |
| Blast radius | Installation and external Elasticsearch failures may affect all hosted tenants |

`namespace_isolated` and `dedicated_installation` are documented future profiles and **unvalidated/unimplemented**. Neither is selectable in v1. A dedicated installation would still require configurable external Elasticsearch; it does not imply a per-tenant Elasticsearch cluster.
