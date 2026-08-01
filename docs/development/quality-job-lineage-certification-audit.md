# Quality, job/run, and lineage certification audit

Audit date: 2026-08-01. Audit base: `53de3d738485d69bcd5bfc71b2038b28afbfcaaa`.

## Preflight

The base history contains merge commits for PR #176 (`1e2d090`), PR #177 (`221b8bc`), and PR #178 (`53de3d7`), with product commits `07ae74e`, `e52e286`, and `b39ed14` respectively. The migration registry terminates at `0021_lineage_analysis_explorer`; the ledger checksum is `48708bb08b183788d378f5666c19ab9d4294d073fca6df44ef1849b7af2bcd7e`.

The checkout supplied to this task has no configured Git remote, so pulling `main` was not possible. A direct unauthenticated GitHub Actions API lookup for each product commit returned HTTP 404; consequently no hosted run or artifact is claimed for those heads.

Existing workflows inventoried before this change were `ci.yml`, `data-product-membership.yml`, `data-product-runtime.yml`, `iam-security.yml`, `job-run-backend.yml`, `lineage-analysis-console.yml`, and `release.yml`. `job-run-backend.yml` only uploaded existing capability reports; `lineage-analysis-console.yml` reran backend tests while assembling its artifact and only compared a text SHA. There was no focused Data Quality workflow. Existing verifier patterns inspected were `scripts/release/verify_certification.py`, `scripts/certification/verify_artifacts.py`, and the independent evidence jobs in the Data Product workflows.

## Certification disposition

This PR defines focused hosted producers and independent consumers for `data-quality-monitoring-v1-evidence`, `job-run-backend-evidence`, and `lineage-analysis-console-evidence`. Metadata binds repository, workflow/run/job identity, event, exact producer SHA, tool and service versions, migration terminal, test totals, and UTC generation time. Verification reparses JUnit XML and rejects provenance mismatch, ambiguity, failures, unexpected security/browser skips, wrong Elasticsearch version, missing PostgreSQL proof, and missing browser/accessibility output.

All affected capabilities remain `functional_unvalidated` (or their existing lower state) until all three workflows execute successfully for the final PR head and their independent verification jobs pass. Hosted workflow URLs and artifact IDs are therefore **not yet available** and are an explicit final-head blocker rather than inferred evidence.
