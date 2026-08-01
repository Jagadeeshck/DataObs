# Incident Workbench architecture

The Incident Workbench is a Team 3 capability behind `/api/v1/incident-workbench`. Authentication middleware establishes tenant identity; request query/body values cannot replace it. Every repository lookup combines that tenant with the selected environment. Production composition injects `ElasticsearchIncidentRepository`; memory storage is only a deterministic local/test option.

## Read model and lifecycle

Inbox predicates execute in Elasticsearch rather than against a 200-item candidate list. Each deterministic sort includes the incident `id` tiebreaker. The repository opens a two-minute point-in-time view and advances it with `search_after`; the signed, versioned cursor binds the PIT and final sort tuple to tenant, environment, complete filters, sort and page size and expires after 15 minutes. Severity uses a fixed runtime keyword-to-rank projection because the released strict mapping has no numeric severity rank; no migration is changed.

The existing legal lifecycle graph remains authoritative. Mutations require the `seq_no:primary_term` revision returned by detail. A stale revision returns HTTP 409 and clients must refresh rather than retry silently. Transitions requiring a reason continue to fail without one.

## Timeline and collaboration

The API event is not indexed directly. The storage adapter maps `timestamp` to `@timestamp`, `event_id` to `correlation_id`, the numeric sequence to mapped `revision`, and actor/event type to bounded `metadata` (with mapped `event_type` also populated). It retains tenant, environment, incident and request IDs and a redacted bounded summary. Elasticsearch `_id` is the deterministic event identity. Reads reverse this translation and sort by mapped `@timestamp` and `correlation_id`, using bounded `search_after` pages.

Protected mutations attribute events only to `request.state.principal.subject`; absence of that validated identity fails closed. Mutations require an idempotency key and use OCC. Before the timeline append, the resulting deterministic event is saved in the released durable action-idempotency resource. If the append fails after the incident update, retrying the same key finds that operation, appends the missing event idempotently, and returns current state without applying the transition again. Elasticsearch still provides no cross-document transaction; a failure before the durable operation record remains an honest error and needs operator investigation.

## Safe actions and approvals

Only the existing Team 3 allowlist can be previewed. Preview output includes allow/deny, risk, approval state, expected changes, target, provider state, warnings and non-sensitive payload-key names. With no executor configured an allowlisted preview is `not_configured`, expected changes are empty, and no execution success is reported. Unsupported actions are denied. Existing durable approval policy requires a pending, unexpired, same-tenant request and separation of requester/approver duties.

Beta 1 does not add autonomous remediation, arbitrary URLs/Kibana calls, provider connectors, Cases synchronization, Workflows deployment, correlation learning, merge/split or flood control.
