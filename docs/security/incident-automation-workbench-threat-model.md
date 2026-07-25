# Incident and Automation Workbench threat model

## Trust boundaries

Findings cross a source-authentication boundary. Every API, Elasticsearch query, SSE replay, Case call and Workflow call is bound to tenant and environment. Browsers receive no provider credentials, connector configuration, raw source payloads or unrestricted workflow output.

| Threat | Mandatory control |
|---|---|
| cross-tenant IDs and SSE leakage | tenant/environment predicates, opaque cursors, authorization before existence disclosure, scoped replay |
| finding spoofing and correlation/severity poisoning | source-bound identity, strict versioned schemas, stable dedup fields, correlation budgets and explainable factors |
| stored XSS and review manipulation | plain text only, output encoding, CSP, human approval for final reviews |
| malicious YAML, deprecated steps, shell/SQL/HTTP, SSRF | safe YAML parser, deny-by-default step and action catalogues, host/connector/workflow allowlists |
| credential interpolation/output leakage | secret references resolved server-side, redaction and response field allowlists |
| approval bypass, self approval and stale approval | distinct scopes, separation of duties, expiry, policy/version/target binding and optimistic concurrency |
| idempotency replay/action substitution/races | tenant-bound keys, immutable preview digest, concurrency key, ETag and append-only decisions |
| audit tampering/evidence deletion | append-only streams, restricted retention, no suppression deletion |
| incident storms and merge/split abuse | quotas, bounded batches/windows, rate limits, preview and audited reassignment |
| connector and Case conflict | configured IDs/spaces only, version reconciliation and error fingerprints |

Autonomous remediation, arbitrary shell/SQL/HTTP, unrestricted `kibana.request`, destructive Kafka/database changes and generic rollback are explicit non-goals.
