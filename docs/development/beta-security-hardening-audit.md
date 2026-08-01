# Beta security hardening preflight audit

## Baseline observed before hardening

Authentication selected local development or OIDC. OIDC verified signature, exact issuer, audience, expiry, issue time, configured asymmetric algorithm, subject and scopes. Discovery was issuer-relative and JWKS had a lock and TTL, but redirect/final-URL, duplicate-key, negative-cache and key-purpose checks required hardening. Identity groups derived roles; tenant selectors were checked against the token tenant claim. Route permissions were selected by path substrings. The only public application endpoints were `/livez`, `/readyz`, `/health`, and `/api/v1/auth/config` (framework documentation is a development facility).

The IAM role-binding dictionary and security-audit list in the API process were **not production durable**. Migration `0020_identity_rbac_tenant_bindings` had already released the exact `dataobs-role-bindings-v1` mutable alias, `dataobs-security-policy-state-v1`, and append-only `logs-dataobs.security-event-*` stream. No released migration may be edited; terminal migration remains `0021_lineage_analysis_explorer`.

Service identity used a username heuristic and required explicit client claim allowlisting. Elasticsearch always used basic authentication with incomplete TLS controls. CORS was not explicitly configured. The API supplied nosniff, referrer and CSP headers but lacked a complete cache/HSTS/permissions policy. The Console already used `oidc-client-ts` Authorization Code flow, state/nonce/PKCE support, sessionStorage, explicit callbacks and no automatic refresh; its `next` destination needed strict same-origin handling.

Secret protection was distributed and did not cover arbitrary diagnostic metadata. Production already rejected local authentication, memory product storage, unsafe OIDC algorithms, absent credentials and disabled TLS validation, but did not reject claims-only authorization, HTTP Elasticsearch, embedded URL credentials, or unsafe CORS. The hardening adds those fail-closed checks.

## Result and limitations

Authorization is now configured as `claims`, `bindings`, or `intersection`; production rejects claims-only. Fixed migration aliases back OCC-backed role bindings and append-only audit events. Explicit method/template policies deny unknown routes. Token lifetime, party/type, service-client, critical-header and JWKS bounds are enforced. Remaining certification limitations are operational: hosted Elasticsearch/OIDC restart and key-rotation evidence must execute before capability status can become `certified`; bootstrap should be disabled after initial bindings; recovery requires a controlled bootstrap configuration change.
