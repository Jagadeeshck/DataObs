# Data Product 360 threat model

## Assets and trust boundaries

Tenant/environment context is supplied only by trusted authentication middleware. Elasticsearch indices are fixed and strict; scoped document IDs prevent overlapping business IDs from colliding. Stored evidence is metadata-only and must never contain raw rows, Kafka bodies, credentials, raw SQL, or unbounded payloads.

## Threats and required controls

| Threat | Control and test |
|---|---|
| Cross-tenant product, member, or dependency probing | scope every ID and filter; return not found |
| Forged ETag or concurrent overwrite | compare If-Match and Elasticsearch sequence/primary term |
| Cursor tampering, expiry, cross-route replay | versioned route-bound HMAC cursor with expiry |
| Graph exhaustion | bounded depth/node count and visible truncation |
| Proposal poisoning/source substitution | validate scope, monitor compatibility, evidence references and confidence |
| Reliability manipulation or stale-as-healthy | bounded finite values; stale/missing excluded and reported; no evidence is unknown |
| Stored XSS or unsafe support/on-call URL | escape rendering and allow only safe URL schemes |
| Oversized payload or replay | request caps and deterministic idempotency IDs |
| Audit divergence | reject divergent same-revision immutable events |
| Sensitive evidence leakage | sentinel scan for secrets, raw rows, Kafka bodies, and SQL |

The security gate must test all controls against two tenants with overlapping product IDs. Until those tests and hosted evidence pass, release readiness is **blocked**.
