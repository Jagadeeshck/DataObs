# DataObs Beta security

Production uses OIDC for identity and `bindings` (or deliberately `intersection`) for authorization. Durable bindings use the migration-0020 alias, scope roles to tenant and optional environments, reject unknown roles, use ETags/OCC, disable rather than delete, and protect the final platform administrator. Bootstrap trusts only configured OIDC groups and must be disabled after creating durable administrators.

Service principals are explicit allowlisted `client_id`/`azp` identities. They require active `service` bindings and receive only tenant/environment-scoped permissions; user groups never elevate them. OIDC requires HTTPS, explicit audience, asymmetric algorithms, bounded size/skew/lifetime, subject, expiry/iat, optional nbf, party and token-type checks. JWKS discovery is same origin and effective port, bounded, signing-only, duplicate-kid rejecting, single-flight and negative cached for unknown keys.

Security events append to `logs-dataobs.security-event-*`; tokens, headers, claims, credentials, secret references and raw IPs are prohibited. Retention is an Elasticsearch lifecycle operations responsibility. Exact CORS origins, trusted proxies, HTTPS-authoritative HSTS and Elasticsearch TLS/credential Secret references are required in production. Rotate OIDC and Elasticsearch secrets, inspect denial/audit signals, and disable bootstrap after commissioning. For IAM lockout, use reviewed bootstrap configuration, restore an administrator binding, verify audit evidence, then disable bootstrap again.

Known limitation: hosted real-stack evidence is required before `functional_unvalidated` can be promoted to `certified`.
