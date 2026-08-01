# Stream reliability data handling

Tenant and environment come only from authenticated request/worker context and are mandatory in definitions, evaluations, status, leases, and signals. Reads use fixed aliases, exact term filters, bounded time ranges and page sizes, safe source allowlists, deterministic sorting, and signed cursors bound to filters. Mutations require idempotency for create and `If-Match` revisions for update/delete.

Evidence contains scalar values, bounded reason codes, missing-input names, and opaque references. It must not contain connector configuration, credentials, Kafka authentication material, full schemas, or source payloads. Logs use IDs and reason codes rather than complete documents. Zero is retained; absence is `null`. Signals contain no root-cause or remediation claim and are handed to Team 3 only through a future stable public intake contract.
