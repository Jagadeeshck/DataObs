# Beta security hardening preflight audit

Before v1, OIDC signature, issuer, audience, expiry, issued-at, subject, algorithm and scope checks existed, with same-origin JWKS discovery and a TTL cache. Roles came from configured group mappings and the tenant selector was checked against token claims. Route permissions were selected with substring matching. Public endpoints were `/livez`, `/readyz`, `/health`, and `/api/v1/auth/config`.

The IAM role-binding dictionary and security-event list were process-local: **the current in-memory IAM and audit stores are not production durable**. A `preferred_username` heuristic identified services. Elasticsearch construction always sent basic authentication and omitted CA/fingerprint controls. CORS was not explicitly configured; basic API headers existed. The Console already used `oidc-client-ts`, PKCE, and session storage.

Migration `0020_identity_rbac_tenant_bindings` released `dataobs-role-bindings-v1`, `dataobs-security-policy-state-v1`, and `logs-dataobs.security-event-*`; terminal migration remains `0021_lineage_analysis_explorer`. This hardening uses those names without changing a migration.

The hardened boundary separates identity validation from scoped authorization, provides bounded JWKS rotation and negative caching, fixed Elasticsearch repositories, exact route-template policy, request metadata validation, CORS/security headers, redaction, and production fail-closed validation. Remaining limitations are that real-stack hosted evidence must execute before certification, security-event retention is an operator-managed Elasticsearch lifecycle concern, and bootstrap should be disabled after durable administrators are established.
