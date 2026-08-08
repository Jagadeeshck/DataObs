# Data contract data handling

Contracts contain declarative schema and evidence references, never credentials, secrets, connection strings, private keys, raw rows, raw payloads, arbitrary SQL, Python, or shell. Actors come only from the authenticated principal. Approval binds tenant, environment, contract, version, and fingerprint. Every repository query includes tenant and environment. Lifecycle writes require scoped idempotency and draft edits require `If-Match`.
