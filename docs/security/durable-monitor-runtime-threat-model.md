# Durable monitor runtime threat model

## Assets and trust boundaries

Monitor definitions, immutable observations/baselines/evaluations, scoped leases, fencing tokens, checkpoints and audit events cross API, runtime, Elasticsearch and provider boundaries. PostgreSQL credentials remain secret references and never enter a monitor or evidence document. Development authentication is **not production authorization** and release readiness is blocked.

## Threats and controls

* **Cross-tenant access:** tenant and environment are mandatory filters and components of deterministic IDs; overlapping business IDs require isolation tests.
* **Lost updates, lease theft, stale workers:** mutable records use Elasticsearch OCC. Lease takeover requires expiry and increments a fencing token; runtime commits must validate the current token.
* **Replay and divergence:** immutable IDs are deterministic; exact replay is a no-op and a different payload raises a consistency error. Event-first reconciliation is explicitly not a cross-index transaction.
* **Cursor tampering/query abuse:** API cursors must be signed/versioned and all page, history, catch-up, metadata, provider-call, response-byte and timeout budgets are capped.
* **Provider/SQL injection:** providers accept typed targets. PostgreSQL accepts only the aggregate AST, validates and quotes allowlisted identifiers, uses read-only transactions and statement timeout, and returns no rows or samples.
* **Secret and payload leakage:** raw SQL, credentials, database rows, Kafka bodies and unbounded backend errors are prohibited. Evidence contains bounded references only.
* **Baseline poisoning:** baseline input is bounded, precedes evaluation time, records exclusions and cannot produce a learned breach before maturity except a fixed safety bound.
* **Suppression/recommendation abuse:** suppressions require actor, reason, approval and bounded duration; evidence remains visible. Recommendations never auto-apply or auto-enable.
* **YAML and stored XSS:** safe YAML parsing, size/item caps, strict schema, no tenant override, raw SQL or secrets; clients must render names/reasons as text.
* **Audit divergence:** canonical checksums and immutable events detect same-revision divergence; reconciliation checkpoints and telemetry expose pending/failed work.

Residual risks include development auth, missing hosted certification, backup/restore, and Kubernetes production certification.
