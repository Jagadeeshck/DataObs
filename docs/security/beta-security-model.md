# Beta security model

DataObs Beta uses an OIDC resource-server boundary. Production requires an HTTPS issuer, explicit audience and asymmetric signing-algorithm allowlist. JWT issuer, audience, expiration, issued-at, optional not-before and subject are validated with bounded skew. Malformed tokens, `none`, unexpected algorithms, unknown keys and missing mandatory claims fail closed without returning token content.

JWKS discovery is issuer-origin constrained, uses bounded timeouts and a 1 MB/100-key response ceiling, rejects malformed or duplicate key identifiers, caches keys, and performs at most one controlled refresh for an unknown `kid`. A known signing key may remain usable for the configured short last-known-good interval during provider failure; an unknown key never does. Production URL validation requires HTTPS.

Every registered `/api/v1` operation is either the explicitly public authentication configuration endpoint or maps through `src/security/route_policy.py` to one permission. The registry checker rejects uncovered routes, stale rules and accidental public routes. Tenant and environment selectors only narrow authenticated bindings; they never create access. Collection ingestion, operational access, IAM administration, workflow approval and platform administration remain separate permissions.

Security events use a fixed v1 allowlist: type, outcome, reason, principal identifier, authorised tenant/environment, request ID, route template, timestamp, source and schema. Token/header/cookie/credential/claims/body fields cannot be supplied to this constructor. Append-only persistence remains the target semantics.

The Console contract remains Authorization Code with PKCE S256, state validation, nonce validation where applicable, safe callbacks, and memory/session-scoped token handling rather than local-storage bearer persistence. Hosted browser/OIDC evidence for the candidate commit is required before Beta certification.

These controls are implemented and locally testable. They are not a production-readiness claim; hosted negative-path, Keycloak and exact-commit evidence remains a release gate.
