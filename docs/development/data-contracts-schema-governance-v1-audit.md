# Data Contracts and Schema Governance v1 audit

- Base SHA: `ee8bb0363df503e60c85136f6d46ecb6ce606633`; final SHA: populated by Git commit/PR metadata.
- Migration: terminal moves from `0026_stream_anomaly_retention_intelligence` to append-only `0027_data_contracts_schema_governance`.
- Storage: mutable current, health, and runtime-state projections; immutable version/lifecycle (3650d), evaluation (365d), and violation (730d) streams with strict mappings.
- Lifecycle/version: draft, review, approved, active, deprecated, retired, plus rejected history. Approved/active versions are immutable; effective periods cannot overlap.
- Approval: exact tenant/environment/contract/version/fingerprint, trusted principal, reason and time; separation-of-duties is required where configured.
- Compatibility: strict/backward/forward/full/custom-bounded; known widening is explicit and unsupported semantics remain unknown.
- Evaluation: equally weighted available components; unavailable excluded; confidence is available/configured ratio; direct high/critical breaches override score. Zero is evidence, not absence.
- Violations: deterministic, categorized, directness/confidence aware, evidence referenced, and raw-row free. Recovery preserves append-only history.
- Surfaces: initial central Console routes for overview, authoring, Contract 360 and version comparison. Production router wiring remains a limitation.
- Tenant/security: every production read predicates tenant/environment; drafts use OCC; evidence is create-only; authenticated actor and idempotency are required by the service boundary.
- Integrations: monitor IDs consume quality evidence; canonical asset metadata supplies governance; lineage impact is referenced as potential structural impact; product IDs do not change membership.
- Runtime: durable cycle contract is documented; full lease/checkpoint CLI wiring remains incomplete.
- Local tests: focused backend unit tests executed. Full Elasticsearch 9.4.2, Console, Playwright, axe, hosted workflow, artifact and independent verification were not run.
- Workflow/artifact: unavailable; `data-contracts-schema-governance-v1-evidence` not produced. Capability must remain `functional_unvalidated`.
- Rollback: stop evaluator, snapshot/remove mutable projections, retain immutable evidence, and roll back application routing. Never rewrite migration history.
