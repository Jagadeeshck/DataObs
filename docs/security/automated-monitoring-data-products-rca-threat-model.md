# Automated monitoring, Data Products, and RCA threat model

## Trust boundaries and data minimization

The browser uses only the authenticated DataObs API and never Elasticsearch directly. All repositories must filter by tenant and environment. Observations contain aggregate scalars, fingerprints and allowlisted metadata—never PostgreSQL rows, SQL literals, Kafka payloads, repository source, or secrets. Optional sampling is disabled by default.

## Threats and required controls

| Threat | Required control |
|---|---|
| Arbitrary SQL and source overload | Aggregate-only read-only templates; parsed statement allowlist; identifier validation; timeout, row and cost limits; per-source concurrency and rate limits |
| Monitor amplification and poisoned baselines | Durable leases, idempotency, bounded backfill, minimum samples, change/outage reset states, audit and human-approved refresh |
| Cross-tenant baseline or RCA evidence | Mandatory tenant/environment predicates, scoped IDs, authorization tests, and repository-level enforcement |
| Backfill anomalies and missing telemetry | Mark excluded backfills and cold-start/stale states; never score missing evidence as healthy |
| Secret, query-text, row or payload leakage | Secret references only; SQL normalization/fingerprinting; allowlisted fields; structured redaction before storage/logging |
| Source-code leakage | Store commit identity and allowlisted path fingerprints only, not diffs or files |
| Webhook spoofing/replay | Constant-time signature verification, timestamp window, nonce/idempotency storage and rotation; otherwise use pull adapters |
| Stored XSS | Encode output, sanitize links and labels, disallow evidence HTML, Content Security Policy |
| Unsafe inference | Disabled by default, tenant policy, redacted structured evidence, auditable model/prompt/cost, deterministic fallback; summary cannot authorize action |
| Workflow escalation | Allowlisted typed actions, RBAC, approval, dry run, idempotency, audit and verification; no shell, arbitrary URL/SQL or destructive Kafka/database operation |
| Recommendation privilege escalation | Generation grants no source or apply permission; acceptance is separately authorized and audited |
| Namespace takeover | Optimistic concurrency, managed-by ownership, explicit adoption/prune, CI identity scope; never prune UI-managed monitors by default |
| RCA overexposure | Evidence summaries plus opaque document references, least-privilege fetch, bounded retention and access audit |

## Safe custom aggregate contract

Only a bounded scalar aggregate may be returned. Execution must be read-only, single-statement, time limited and row limited. Templates and identifiers are validated server-side; comments, stacked statements, mutations, volatile functions and sensitive literals are rejected. No remediation is autonomous or destructive.
