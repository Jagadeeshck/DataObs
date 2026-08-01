# Team 6 Beta security and release preflight audit

## Audited starting point

The repository snapshot identified as current `main` for this environment was
`6d52eb8e65d47ba9c841800e1bed853de8e5c37f` (the checkout had no configured
remote or local `main` ref). The executable migration manifest contained 21
released migrations and terminated at `0021_lineage_analysis_explorer`.
Immutability was checked against the audited SHA; no released migration or
checksum is changed by this PR.

## Findings

Existing controls included allowlisted OIDC algorithms, mandatory issuer and
audience, bounded clock skew/token size/JWKS timeout and response size, same-
issuer discovery, cached keys with one unknown-key refresh, deny-by-default
permissions, trusted tenant bindings, redacted authentication errors, secured
Helm contexts, digest fields, resources, probes, NetworkPolicies, PDBs, external
Elasticsearch, and bounded Kind/upgrade harnesses. The Console already used
Authorization Code plus S256 PKCE with in-memory token storage.

Existing certification workflows were CI, IAM security, capability-specific
Team 1–5 workflows, Beta deployment packaging, and tag-triggered release. Their
artifacts used capability-specific names; `beta-deployment-packaging-evidence`
was the closest platform artifact. Release already built, generated SBOMs,
scanned before login/push, resolved digests, and emitted a manifest. However its
hard-coded workflow list and artifact validation were incomplete and its old
known-limitations/terminal-migration metadata conflicted with the executable
manifest. Deployment scripts were authoritative rather than duplicated, but
hosted durability/backup evidence was absent.

## Selected change and gaps

This PR adds the Team 6 live-route drift gate, explicit public policy, exact-
commit manifest/verifier, dispatch-only least-privilege orchestration, backup and
restore commands, evidence naming, and truthful security/operations/rehearsal
documentation. The only shared implementation edit is the minimal API policy
classification for dataset/entity reads and the migration status endpoint; no
capability behavior or API contract changes.

Hosted Kind/Elasticsearch 9.4.2, Keycloak, restart durability, backup/restore,
browser, image scan, SBOM, provenance, and release publication evidence remains
pending. Team 1–5 must produce their mandatory exact-SHA artifacts. RPO/RTO is
unmeasured. No hosted artifact for this commit existed during preflight, so this
PR neither certifies Beta 1 nor claims production readiness.
