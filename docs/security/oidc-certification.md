# Production-like OIDC certification

A disposable IdP is a CI dependency and is not a Helm workload. Hosted certification must use Authorization Code with PKCE S256 and cover state, nonce, issuer, audience, authorised party, signature, claims, lifetime, token type, JWKS caching/rotation/last-known-good expiry, duplicate and unknown keys, expired/future tokens, logout/session expiry, group roles and deny-oriented defaults. Secured Elasticsearch must require a dedicated DataObs identity and certificate verification; an `xpack.security.enabled=false` run cannot satisfy this gate.

Evidence is `identity-certification-report.json`, redacted JUnit, and `security-redaction-report.json`. Tokens, secrets, passwords, private keys, full authorization headers and sensitive claims are forbidden. Hosted exact-SHA evidence is **pending**.
