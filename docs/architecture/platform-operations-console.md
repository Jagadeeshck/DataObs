# Platform Operations Console architecture

The Admin workspace route is a read-first orchestration layer. It issues the seven independent platform reads in parallel, supplies abort signals, applies two-second provider timeouts, deduplicates concurrent identical reads and retains successful panels when another provider fails. Refresh is manual; there is no polling.

Fleet-wide requests deliberately omit the active product tenant header. Authentication and `platform_operations:read` remain backend authoritative. Detail routes are permission-gated and API failures reveal no entity metadata. The package contains presentation types and state labels—not lifecycle transition logic.

Observe is implemented. Plan, Approve, Execute and Verify are labelled operational handoffs. Deployment plans and promotion validation are excluded because their contracts lack the full OCC, idempotency and preview safeguards required for browser mutation in v1.
