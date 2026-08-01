# Incident Workbench architecture

The Incident Workbench is a Team 3 capability behind `/api/v1/incident-workbench`. Authentication middleware establishes tenant identity; request query/body values cannot replace it. Every repository lookup combines that tenant with the selected environment. Production composition injects `ElasticsearchIncidentRepository`; memory storage is only a deterministic local/test option.

## Read model and lifecycle

Inbox reads are bounded to 100 records, deterministically sorted, and paged with an opaque cursor bound to tenant, environment, filters, sort and page size. Detail responses distinguish absent evidence (`unknown` plus a missing input) from measured values including zero. Findings are represented by bounded references and evidence is recursively size-limited and secret-key redacted.

The existing legal lifecycle graph remains authoritative. Mutations require the `seq_no:primary_term` revision returned by detail. A stale revision returns HTTP 409 and clients must refresh rather than retry silently. Transitions requiring a reason continue to fail without one.

## Timeline and collaboration

State, assignment and comment mutations append immutable events containing scope, incident/event identity, UTC timestamp, actor, safe summary, revision and request correlation. Event IDs make retryable comments idempotent. Timeline order is timestamp then event ID. Production events use the released `logs-dataobs.incident_comment-*` resource; history is never updated in place.

## Safe actions and approvals

Only the existing Team 3 allowlist can be previewed. Preview output includes allow/deny, risk, approval state, expected changes, target, provider state, warnings and non-sensitive payload-key names. With no executor configured an allowlisted preview is `not_configured`, expected changes are empty, and no execution success is reported. Unsupported actions are denied. Existing durable approval policy requires a pending, unexpired, same-tenant request and separation of requester/approver duties.

Beta 1 does not add autonomous remediation, arbitrary URLs/Kibana calls, provider connectors, Cases synchronization, Workflows deployment, correlation learning, merge/split or flood control.
