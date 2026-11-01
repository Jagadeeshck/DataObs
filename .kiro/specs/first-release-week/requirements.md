# Requirements — first supported DataObs release (week ending 2026-11-06)

## Purpose
Deliver the smallest evidence-backed and supportable DataObs distribution while preserving the six-pillar roadmap. Current v1.0.0 / ES 9.5.5 source announcement is not itself a successful release.

### Functional requirements
- R1: Secure, tenant-scoped API and Console package can be installed, started, and used via one documented supported deployment profile.
- R2: First release demonstrates an end-to-end observed signal → context → finding → canonical incident → authorized retrieval journey. Include Streams/Pathways, Jobs/Run, Quality, Lineage and Data Products only as the bounded certified matrix allows.
- R3: Missing/unknown/stale/partial/zero evidence is accurately reported and traceable to source.
- R4: Provider support statements match actual packaged and hosted-certified runtimes, not registration or mocks.
- R5: Production safety: OIDC/JWKS/RBAC, tenant/environment isolation, least privilege, audited and approval-bound actions.

### Nonfunctional requirements
- R6: Exact-SHA complete CI: shared checks, real ES migration (first and repeat), Kubernetes/Helm smoke, Compose MVP, destructive backup/restore, browser/a11y, security, SBOM/signatures/provenance.
- R7: One internally consistent version and support matrix, including Elasticsearch and Python client compatibility.
- R8: Independently verified artifact digest/run/SHA/attempt, supported platform, security PASS and protected authority GO before publication.
- R9: No edits to released migrations or downgrades of security/mandatory checks.

### Acceptance
Given a clean supported environment, when operator follows release install docs, then API+Console start, safe authenticated tenant flows work, migrations repeat safely, E2E journeys are correct, destructive restore succeeds, browser/a11y suites pass and the release authority produces independently verified GO.

**If any acceptance fails: NO_GO; an internal evaluation build may be documented but not called a supported release.**
