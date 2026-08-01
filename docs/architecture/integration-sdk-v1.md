# Integration SDK v1

## Status and scope

The Team 4 Integration SDK is **implemented, functional_unvalidated**. Local tests do not constitute hosted
certification. It is a provider-neutral collection contract and does not claim that AWS or any other new provider is
supported. PostgreSQL continues through its existing scanner contract; Kafka, Airflow, dbt, and Spark remain owned by
Teams 1 and 2.

## Architecture and lifecycle

`packages.collectors.sdk` defines immutable context, configuration, capabilities, requests, checkpoints,
observations, errors, retries, and an explicit provider registry. Collection Manager's `ProviderRuntime` performs:

1. trusted tenant/integration context verification;
2. explicit registry lookup (never a configuration-driven import);
3. capability negotiation and provider validation;
4. timeout-bounded asynchronous iteration with bounded retry;
5. observation-count limiting and deterministic overlap suppression; and
6. optimistic checkpoint advancement after successful iteration.

Cancellation is not swallowed. Provider instances are created per execution. A provider must bound its own API page
size and use `DiscoveryRequest`/`CollectionRequest` cursors; the runtime adds a total observation bound. Production
checkpoint stores should implement `CheckpointStore` using the existing Elasticsearch repository and OCC conventions.
The in-memory implementation is test/development-only.

## Capabilities and unsupported operations

Every provider declares supported and unsupported capabilities, required permissions, modes, optional dependencies,
and evidence limitations. Negotiation fails with `unsupported_capability`; it must never return a misleading empty
result. Capabilities include discovery, metadata, metrics, logs, lineage evidence, cost, query history, schema,
health, incremental, and event-driven collection. Declaration does not itself establish support.

## Configuration and credentials

The checked-in v1 JSON Schema is authoritative for documents. Tenant identity is deliberately absent: it comes from
the authenticated runtime. `credential_ref` permits environment, Kubernetes Secret, cloud secret-manager, or external
secret references. Values are resolved outside the SDK and must never enter observations. Raw password, token,
access-key, secret-key, and tenant fields are rejected from provider configuration. Configuration is data only and
cannot identify Python modules or execute code.

## Evidence contracts

Resource IDs hash provider, account/project, region, service, and provider-native ID with explicit separators. Metric
observations require an evidence state: measured zero is represented as `value=0, state=measured`; missing, unknown,
unsupported, stale, and partial states carry no numeric value. Missing evidence must not produce healthy state.
Provider payloads must be normalised and bounded before emission.

Errors have stable codes and retryability separate from text. Authentication, authorization, invalid configuration,
and unsupported operations do not retry. Transient, dependency, throttle, timeout, and checkpoint-conflict errors may
retry under attempt and elapsed-time limits. Retry hints are honored only within the elapsed bound. Persisted error
text must pass `redact_text`/`redact_mapping`.

## Building a provider

Implement the asynchronous `IntegrationProvider` protocol without importing optional dependencies at module import
time. Provide a zero-argument factory and register it explicitly in application composition:

```python
registry = ProviderRegistry()
registry.register(ExampleProvider)  # Explicit trusted code; never a user-supplied dotted path.
```

The example configuration is documentation-only and disabled. A new provider requires deterministic fake-client
tests for validation, connection outcomes, pagination, late-data overlap, cancellation, timeouts, partial failures,
throttling, redaction, tenant separation, stable IDs, and evidence-state semantics. Live credentials are prohibited
from normal CI.

## Telemetry and tenancy

Runtime instrumentation may label only bounded provider type, capability, phase, and result status. Resource IDs,
query text, credential references, and provider error text are prohibited labels. Traces must not include credentials
or raw payloads. Providers receive tenant identity only through immutable `IntegrationContext`; provider responses
cannot change it.

## Certification

Capability status remains `functional_unvalidated` until an exact-commit hosted workflow produces the repository's
standard provenance artifact and a separate verification job succeeds. Evidence must record supported and unsupported
capabilities, fixtures, dependency versions, commands/results, redaction, tenant isolation, and known limitations.
