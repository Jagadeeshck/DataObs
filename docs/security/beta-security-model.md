# Beta security model

DataObs is an OIDC resource server. It accepts only configured algorithms,
requires issuer, audience, subject, issue time and expiry, applies bounded clock
skew, and fails closed for malformed tokens and unknown signing keys. JWKS
discovery is same-origin with the issuer, bounded to a 30-second-style configured
timeout and 1 MB response, cached, and refreshed once for an unknown `kid`.
Production configuration requires HTTPS. Errors contain reason codes, not token
or claim contents.

Tenant and environment selectors only narrow authenticated bindings. The API
route policy separates collector ingestion from operator and IAM permissions;
the live registry checker fails on a protected route without authentication or
on drift in the explicit public allowlist. The sole public `/api/v1` contract is
OIDC configuration. Security evidence may contain identifiers, scope, route,
request ID, outcome, timestamp and schema version, but never authorization
headers, tokens, credentials, cookies, claims, or bodies.

The Console uses `oidc-client-ts` Authorization Code flow with S256 PKCE and its
library-managed state/nonce callback validation. Tokens are held by in-memory
web storage rather than local storage. These implemented controls require exact-
commit hosted negative-path evidence before Beta certification and are not a
production-readiness claim.
