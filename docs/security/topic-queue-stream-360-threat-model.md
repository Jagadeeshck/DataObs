# Topic, Queue, and Stream 360 threat model

## Assets and trust boundaries

Kafka/Connect/Registry credentials remain server-side secret references. Browser clients receive normalized metadata, never Admin clients, SASL/JAAS, raw keys, arbitrary headers, payloads, connector secrets, or schema credentials. Tenant and environment are mandatory predicates at collection, storage, cache, SSE, and query boundaries.

## Threats and controls

| Threat | Controls |
|---|---|
| Credential, JAAS, private-key or connector-secret leakage | `env:`/`file:` references, TLS verification, config allowlists, drop-before-persist redaction, sentinel scans, no browser credentials |
| Malicious names, schema injection, stored XSS | Treat names/schema metadata as data, bounded lengths, strict mappings, output encoding, no rendered HTML |
| Cross-tenant cluster IDs and offset enumeration | Tenant/environment-scoped stable IDs, RBAC/scopes, query predicates, cache-key isolation, denial tests |
| Cardinality and partition-scale denial of service | Include/exclude rules, quotas, batching, checkpoints, adaptive intervals, bounded pagination/aggregation and backpressure |
| Admin API overload or stale/poisoned metrics | Conservative deadlines, retries with jitter, source quotas, observed timestamps, source identity, partial/stale states; missing is never healthy/zero |
| Message inspection abuse and key/header/payload disclosure | Disabled by default, dedicated scope, tenant policy, topic allowlist, explicit reason, short lifetime, byte/message caps, key hashing, header/field allowlists, in-memory redaction, audit only |
| SSRF to Connect/Registry and Kibana URL injection | HTTPS and hostname allowlists, credential-free configured base URLs, safe path quoting, bounded timeout, allowlisted Kibana base URL |
| Unsafe action request | Explicit eligibility and action allowlist, approval, idempotency/concurrency key, audit and verification; offset reset, deletion, reassignment, retention reduction, broker restart, shell and arbitrary URLs forbidden |
| Source spoofing/metric poisoning | Integration identity, evidence references, timestamps, confidence and contradictions; never auto-confirm RCA |

Message inspection remains off with `DATAOBS_MESSAGE_INSPECTION_ENABLED=false`. Autonomous remediation is not supported.
