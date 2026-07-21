# Data Product 360 threat model

## Assets and trust boundaries

Tenant/environment context is supplied only by trusted authentication middleware. Elasticsearch indices are fixed and strict; scoped document IDs prevent overlapping business IDs from colliding. Stored evidence is metadata-only and must never contain raw rows, Kafka bodies, credentials, raw SQL, or unbounded payloads.

## Threats and required controls

| Threat | Control and test |
|---|---|
| Cross-tenant product, member, or dependency probing | scope every ID and filter; return not found |
| Cross-tenant proposal, decision, SLO or evaluation probing | bind storage identity and every read filter to tenant, environment and product |
| Forged ETag or concurrent overwrite | compare If-Match and Elasticsearch sequence/primary term |
| Cursor tampering, expiry, cross-route replay | versioned route-bound HMAC cursor with expiry |
| Graph exhaustion | bounded depth/node count and visible truncation |
| Proposal poisoning/source substitution | validate scope, monitor compatibility, evidence references and confidence |
| SLO identity collision or corrected-evidence overwrite | include full scope, definition revision, window, method and canonical evidence fingerprint in immutable IDs |
| Reliability manipulation or stale-as-healthy | bounded finite values; stale/missing excluded and reported; no evidence is unknown |
| Stored XSS or unsafe support/on-call URL | escape rendering and allow only safe URL schemes |
| Oversized payload or replay | request caps and deterministic idempotency IDs |
| Audit divergence | reject divergent same-revision immutable events |
| Partial migration reported healthy | verify every required resource (including decisions), aliases, strict mappings and write blocks with reason codes |
| Sensitive evidence leakage | sentinel scan for secrets, raw rows, Kafka bodies, and SQL |

The security gate must test all controls against two tenants with overlapping product IDs. Until those tests and hosted evidence pass, release readiness is **blocked**.

## API and Console completion controls

Data Product pagination cursors are canonical JSON signed with HMAC and bind version, resource type, trusted tenant/environment, filter fingerprint, issue time, expiry, and sort values. The API caps cursor and filter sizes and never encodes internal index names. Tampering, expiry, cross-route replay, cross-filter replay, and cross-tenant replay fail closed.

Trusted scope is derived from request middleware, not request bodies. Mutations require ETags and idempotency keys; administrative transitions require actor and reason. Fixed aliases, strict mappings, bounded traversals, create-only evidence, and OCC projections remain mandatory. Console values use React text rendering, unknown evidence is not healthy, and unavailable scoped resources use a non-enumerating not-found state. Unsafe support/on-call URLs, stored XSS, oversized requests, raw backend errors, proposal poisoning, source substitution, duplicate acceptance, evaluation replay, reliability manipulation, and sentinel leakage remain certification cases rather than assumed controls.
