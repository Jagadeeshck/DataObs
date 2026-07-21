# Incident concurrency operations

Incident creates are create-only and updates use Elasticsearch optimistic concurrency. Mutation-capable searches request sequence number and primary term. Exact and stale replay paths do not issue an incident write and therefore do not advance the sequence number.

Operators should alert on `incident_ingest_conflict_total` and `incident_ingest_retry_exhausted_total`, correlate using the request ID in redacted logs, and avoid labels containing tenant, incident, finding, or asset IDs. Other counters distinguish created, updated, exact replay, stale replay, and retries.

## Reconciliation

After a 409, confirm the finding exists in the fixed findings read alias, inspect the incident by tenant/environment/deduplication key, and replay the sanitized source event. A replay re-merges missing monotonic assets or newer projection values. Never edit sequence metadata, bypass aliases, enable dynamic mappings, or retry by creating a different incident ID. Escalate repeated exhaustion with request ID, event time, bounded source/finding type, and redacted Elasticsearch logs.

Rollback is an application rollback only: migrations 0001–0012 and strict mappings are unchanged. Roll back all workers together only to a release that uses the v1 two-part incident-ID formula.
