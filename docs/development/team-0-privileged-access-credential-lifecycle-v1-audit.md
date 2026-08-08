# Team 0 privileged-access and credential-lifecycle v1 audit

## Audit identity

Audited base SHA: `c5b7dff6573b6fd0ce76122e7112b726c35d431d`. The checkout has no configured Git remote, so that locally available merge commit is the strongest available base evidence. The executable registry command `python scripts/release/current_terminal_migration.py` reports `0025_stream_pathway_reliability_production_closure`; the next forward identifier would be 0026. This change does **not** add a migration because durable projections and APIs are not yet complete.

## Findings

Reusable controls include OIDC/JWT authentication, fail-closed route templates, tenant/environment intersection, canonical roles, deterministic role-binding IDs, an Elasticsearch role-binding adapter, strict security-event data stream, OCC-style ETags, Helm secret-name/key references, release evidence validation, secured-Elasticsearch tests, and hosted OIDC fixtures. Runtime IAM handlers nevertheless read `app.state.role_bindings`, bypassing the durable adapter constructed at startup. The last-administrator check is read-count-then-write and races. Listing lacks signed contextual cursors and filters. Audit persistence has append-only writes but no bounded read contract. Effective access, service-principal lifecycle, break glass, privileged plans, credential inventory, and rotation APIs are absent.

Existing references cover Kubernetes Secret names/keys, Elasticsearch password/API key and CA, OIDC client/JWKS trust, OTLP headers/CA/certificates, snapshot credentials, ingress TLS, image pulls, and provider references. Cursor HMAC keys can support overlap through the added storage-neutral keyring; most other runtime references are not yet rotation-capable. OIDC signing keys remain provider-owned. Secret creation and provider-specific use remain Teams/platform operators and Team 4; console presentation remains Team 5.

## Risks and evidence

Process-local IAM loses state on restart and can disagree with authorization resolution. Concurrent final-admin revocation is unsafe. Missing bounded reads can encourage unsafe direct datastore access. Missing evidence is never treated as healthy. Local unit evidence exists for separation of duties, strong authentication, scoped expiry, rotation ordering, metadata-only inventory, and HMAC overlap. Durable integration, real Elasticsearch/OIDC, Kind, backup/restore, support-bundle, and exact-SHA hosted evidence are **pending**; release certification is therefore blocked.

## Executable terminal migration

Run `python scripts/release/current_terminal_migration.py`. It returns `0025_stream_pathway_reliability_production_closure`. No released migration was modified and no 0026 migration is registered in this partial implementation.
