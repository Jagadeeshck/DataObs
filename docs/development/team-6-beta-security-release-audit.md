# Team 6 Beta security and release preflight audit

## Audit identity and product truth

The audited `main` baseline is commit `6d52eb8e65d47ba9c841800e1bed853de8e5c37f`. The exercise checkout did not contain a configured remote; an authenticated fetch of the private repository was unavailable, so this SHA is the newest supplied merged-main commit and is the explicit comparison base. No Team 1–5 branch was merged, rebased, or copied. The executable migration manifest ends at `0021_lineage_analysis_explorer`. The pre-change immutability check was run against the supplied base; this PR does not add or alter a migration.

This audit records repository definitions, not hosted success. No exact-commit hosted Team 6 artifact for this change existed during preflight. Beta 1 and production readiness therefore remain unclaimed.

## Existing controls

### Identity, tenancy, and audit

* `src/security/` already provided explicit asymmetric algorithm configuration, issuer/audience verification, bounded token length and skew, JWKS discovery/cache, trusted group-to-role mapping, deny-oriented roles, and principal-bound tenant/environment selection.
* Production configuration already required OIDC, HTTPS issuer, an audience, asymmetric algorithms, Elasticsearch authoritative storage and TLS verification.
* API dependencies protected nearly all operational endpoints, with `/api/v1/auth/config` intentionally public. The permission choice was a path-keyword heuristic with a broad platform-administrator fallback, however, and there was no registry drift check.
* IAM objects were tenant-filtered and mutations emitted in-memory append-only events, but those events did not use the complete bounded security-event envelope.
* Console architecture documents and implementation describe Authorization Code with PKCE S256, state/nonce checks and session-memory tokens. Hosted browser verification for the audited SHA was not retained.

### Elasticsearch and deployment

* The migration registry contained 21 forward migrations and checksum governance. Migration `0020` owns role bindings, policy state, and append-only security events; existing resources can support this work.
* The Helm chart already packaged API, Console, workers, migration Job, service accounts, NetworkPolicies, disruption budgets and production digest values. It references external Elasticsearch and does not package Elasticsearch or an identity provider.
* `chart_assertions.sh` checked component presence, one migration Job, basic pinning, policies, disruption budgets and minimal rendering. It did not structurally check every container security context, probes, resources or host namespace.
* Kind smoke and Helm upgrade harnesses already used bounded Helm/kubectl waits and explicit exit 77 when prerequisites were absent. Coverage was foundational rather than retained HA/product-state certification.

### Certification and release

Existing capability workflows were inspected: `ci.yml`, `iam-security.yml`, stream/pathway, data-quality, job/lineage, data-product, cluster/connector Console, deployment packaging, delivery foundation, reusable backend/Console validation, and `release.yml`. Producers use multiple capability-specific artifact names. `scripts/certification/provenance.py`, `verify_artifacts.py`, and `scripts/release/verify_certification.py` are authoritative existing evidence utilities.

The tag release workflow already builds images, creates SBOMs, scans before login/push, publishes digests, and creates a prerelease manifest. Its static required-workflow list and older release-manifest limitations conflict with current Beta closure needs. The new Beta workflow is dispatch-only and does not replace the tag release workflow. Certification compose wrappers overlap operationally but serve different stack/bootstrap phases; no duplicate chart validator was added.

No retained local file proves that the defined hosted artifacts succeeded at the audited SHA. The product evidence index correctly reports missing or defined-not-run hosted evidence.

## Gaps selected for this PR

1. Replace heuristic v1 authorization with an explicit route-template policy, fail unknown routes closed, and validate the live FastAPI registry deterministically.
2. Tighten JWKS response/key bounds, duplicate-key rejection, required JWT claims and time-limited last-known-good behavior.
3. Constrain Team 6 IAM audit events to a fixed, bounded, redaction-safe envelope and recursively test the contract.
4. Structurally assert production chart image pins, non-root/read-only/capability/seccomp controls, resources, probes, host namespaces, plaintext-secret patterns and absence of embedded Elasticsearch/identity resources.
5. Retain the existing bounded deployment harnesses as authoritative and document precisely what hosted execution must prove.
6. Add external-Elasticsearch snapshot backup/restore commands and a Beta recovery contract without embedding credentials.
7. Add a manifest-driven exact-SHA verifier with deterministic tests for missing, failed, ambiguous, stale and incompatible evidence.
8. Add one dispatch-only Team 6 candidate workflow with read-only defaults and a separate protected publication job. Build, SBOM and vulnerability scan occur before registry permissions/authentication.
9. Add truthful security, recovery, HA and release-rehearsal documentation.

The only shared implementation file changed is `src/api/app.py`: a minimal replacement of route permission selection and construction of the two existing IAM security events. `src/config/settings.py` adds one bounded JWKS last-known-good setting. No capability behavior or API schema changes are introduced.

## Deferred work and dependencies

* Team 1–5 must execute their declared workflows for the exact target SHA with unique, compatible evidence. Missing mandatory evidence is `fail`; optional missing evidence is `pending`, never pass.
* Kind restart, replacement, uninterrupted-availability, duplicate-evidence and lease-expiry scenarios require digest-pinned runnable images and hosted infrastructure. Scripts define bounded local entry points; results are pending until executed and retained.
* Snapshot restore requires an administrator-controlled Elasticsearch snapshot repository and a destructive recovery environment. Hosted restore/tenant-isolation evidence is pending. RPO and RTO are unmeasured.
* Console PKCE behavior remains locally inspected; exact-SHA browser and identity-provider evidence is pending.
* Vulnerability databases, registry digests, Kubernetes versions, SBOMs and provenance exist only after the candidate workflow runs. This PR configures generation but does not claim those artifacts already exist.
* Beta support is conditional on every mandatory exact-commit gate. This PR is a certification foundation and is not itself a Beta 1 or production certification.
