# Team 0 security compliance and evidence posture v1 — latest-main audit

* **Audited clean main-equivalent SHA:** `ad31a9a38d69dd98b2191318b331a7134f5339e4` (the supplied checkout had no `main` ref or remote; this clean merge commit was the repository tip before work began).
* **Terminal migration (derived):** `0033_team1_stream_schema_intelligence_runtime`, produced from the executable registry by `scripts/release/current_terminal_migration.py`; it was not hardcoded.
* **DataObs / Helm chart version:** `0.2.0` / `0.2.0` (`helm/dataobs/Chart.yaml`).
* **Release decision:** `NO_GO`; retained candidate evidence identifies missing deployment, independent verification, recovery, redaction, security, tenant, rollback, and vulnerability results.
* **Supported-platform state:** the matrix is narrow and does not establish current release readiness; Kubernetes 1.30 is the chart target.
* **Migration decision:** no migration. Posture v1 is repository metadata, validation, CI, and a bounded API view.

## Existing implementation inventory

| Area | Audited foundation | Evidence posture at audit |
|---|---|---|
| Security packages | `src/security`, platform operations, executable migration/release/security scripts | implementation exists; exact-SHA aggregate absent |
| Authentication | OIDC/JWT validation, issuer/audience/expiry/type rules, PKCE and JWKS documentation/tests | local evidence exists; hosted OIDC evidence missing |
| Authorization | permissions, canonical roles, bindings, route policy, last-admin protections | route checker exists; hosted authorization evidence missing |
| Tenant isolation | tenant/environment context, lifecycle and profile documentation/tests | locally tested; hosted adversarial evidence missing |
| Privileged access | request/approval, no self-approval, expiry, strong-auth, revocation, break-glass and audit lifecycle | locally tested; current production evidence missing |
| Credentials | rotation, overlap, metadata-only inventory, expiry and secret references | foundations/local tests; production rotation evidence missing |
| Audit logging | structured security audit events and persistence-failure runbook | local coverage; aggregate safety evidence absent |
| Secrets | Helm/Kubernetes references, integration contracts, support redaction | local controls; repository-wide bounded validation absent |
| TLS/encryption | Elasticsearch verification, OIDC HTTPS, ingress/provider requirements | deployment responsibility; no application at-rest encryption claim |
| Kubernetes/NetworkPolicy | PSS Restricted, non-root, seccomp, capabilities, privilege escalation, digest, service account, RBAC, NetworkPolicy and optional admission reference | validators exist; observed hosted state missing |
| Supply chain | SBOM/provenance/signing/digest framework and candidate workflows | tooling exists; this SHA has no retained independently verified chain |
| Vulnerabilities/dependencies/licenses | Python, Node and image scanning appear across security/release/provider workflows; license checks exist in release foundations | no canonical aggregate current-SHA result |
| Migration integrity | executable manifest, graph and immutability checks | terminal derivation utility was broken by missing symbols and repaired in this PR |
| Backup/restore | manifest scoping, destructive guards, recovery verification and secret exclusion docs/scripts | simulation/local foundations; current hosted recovery evidence missing |
| DR/resilience | dependency and DR certification workflow | workflow is not hosted/certified evidence; current evidence missing |
| Support bundle | v2 allowlisting, bounds, redaction, fingerprinting and no raw dumps/logs by default | local evidence references; current exact-SHA aggregate absent |
| Threat models | many subsystem-specific security and data-handling documents | 11 registered current scopes; Elasticsearch, collectors and CI/CD need dedicated models |
| Exact-SHA/hosted evidence | certification envelopes, release authority, Kubernetes/hosted workflows | workflow presence is not hosted validation; candidate artifacts target another SHA |
| Waivers/exceptions | Kubernetes policy exception schema; no canonical general/CVE register | no active canonical exceptions discovered |

## Known blockers and ownership

* Missing current-release hosted tenant isolation, OIDC/TLS, backup/restore, and DR evidence — Platform, Authentication, and Operations teams.
* Missing exact-SHA SBOM, vulnerability aggregate, provenance, signature and independent verification — Release and Security teams.
* CI workflow least-privilege findings require review rather than a wholesale rewrite — Release Team.
* Current release authority remains `NO_GO`. These are machine-readable in `security-findings.yaml` and the generated posture/release gate.
