# First release decision plan — week of 2–6 November 2026

**Target:** Friday 6 November 2026. **Candidate label:** resolve version consistency before naming a tag. GitHub `main` on 2026-10-31 references v1.0.0 and Elastic 9.5.5, but tracked production readiness remains v0.2.0 / NO_GO. Treat 1.0.0 as **unverified release candidate**, not a published, certified production release.

## Monday — triage/version truth (Team 0 leads)
- Refresh exact `main` SHA and completed Actions; inspect the Release workflow error and all mandatory producers.
- Audit `RELEASE.md`, `README.md`, Docker/Compose/Helm, `ui/dataobs-console/package.json`, Python Elasticsearch client, generated schemas, migration terminal, product ledger and release authority.
- Decide version and compatible profile explicitly; do not silently repin Elastic. Track v1.0.0 + ES 9.5.5 only if targeted workflows actually support it; otherwise retain NO_GO and propose bounded supported candidate.
- Classify failures: common bootstrap/version vs domain/backend vs browser vs supply-chain.

## Tuesday — shared fixes (Team 0), parallel domain triage (Teams 1–5)
- Fix root causes in shared CI, authenticated clean migrations, API startup, Helm/Kind and Compose, and destructive recovery.
- Teams 1–5 prepare minimal owned fixes; preserve passing suites. Team 5 closes common Console formatting/browser blockers; Team 2 verifies full Quality → incident path.

## Wednesday — merge and revalidate
- Merge **Team 0 shared prerequisite fixes first if needed**; otherwise Team 5 common Console fixes first, then Team 2, Team 1. Team 3 and 4 only if a mandatory defect exists.
- Each merge invalidates previous SHA-based release evidence. Re-run mandatory Gate 0 checks on final integrated `main`.

## Thursday — freeze and certify
- Freeze exact candidate SHA **only after Gate 0 green**. Run canonical workflow_dispatch producers for Team 1–5 plus first supported platform certification.
- Verify Elasticsearch version/client, OIDC/JWKS/TLS, tenant A/B/C denial, real-Kafka / OTel / OpenLineage, browser and axe, backup/restore, SBOM, provenance, signatures and digest-pinned install.
- Independent verifier must accept each complete artifact/run/attempt; no mandatory skip.

## Friday — release decision
- Formal security release gate PASS + supported platform approved + immutable artifacts and independent release authority GO -> release tagged/signed artifacts and publish exact support matrix and limitations.
- Otherwise report **NO_GO**, publish no supported-release claims, retain a verified internal evaluation RC only if its bounded certification is complete, and prioritize blocker follow-up.

## Candidate first-release scope
- Packaged API + standalone Console, tenant-scoped Elastic storage/migrations, OTel ingestion and core monitor/incident lifecycle.
- Include streams/pathways, Quality, Job/Run, Lineage and Data Product features only when their mandatory hosted producer + independent evidence pass at exact SHA.
- Provider SDK and registered Collection Manager integrations may remain **experimental** if not packaged. Avoid broad AWS/Snowflake/Databricks/database marketing claims.
- FinOps, Business and AI/Agent pillars stay roadmap unless their specific production evidence is accepted.

## Stop conditions
- Migration inconsistency; API/Console won't start clean; destructive recovery missing; tenant escape; wrong/unknown OIDC; missing browser/a11y proof; skipped mandatory test; no supported platform; failed signature verification; mismatch v0.2/v1.0 or ES versions; release authority NO_GO.

## Required proof
Exact commit SHA + workflow identity/run/attempt + artifacts + external test environments/version + JUnit + no mandatory skips + independent validation + final release authority; maintain `docs/release` machine-readable sources, don't edit generated truth manually.
