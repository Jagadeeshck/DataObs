# Console cross-capability navigation

`src/app/entityLinks.ts` is the canonical resolver for Incident, Monitor, Job,
Run, Pathway, Kafka cluster, Topic, Consumer group, Connector, Schema subject,
Data product, Asset, and Integration links. Identifiers are length/control-byte
validated and encoded as one path segment. Unknown types and malformed IDs
return `null`, requiring callers to render non-link text.

Tenant, environment, and time range are propagated by shared product context,
not embedded into entity identifiers. Only allowlisted, non-secret query state
may be retained. Tokens, raw provider configuration, evidence payloads, and
browser-supplied tenant identity must never enter a URL or navigation state.
Capability pages should migrate local concatenation to this resolver when their
owning team next changes those surfaces; Team 5 does not rewrite their logic.
