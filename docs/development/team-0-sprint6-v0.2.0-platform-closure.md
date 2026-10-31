# Team 0 Sprint 6 v0.2.0 platform closure

## Scope and release truth

- Audited main: `eb9dff57820b39c3dd33a98f834498c30f644d89`
- Sprint 6 branch: `codex/sprint6-team0-platform-closure`
- Target: `v0.2.0`
- Current release decision: **NO_GO**
- RC freeze: **not authorized**
- Publication: **not authorized**

This closure changes shared platform/release infrastructure only. It does not add
features, edit released migration definitions, skip mandatory tests, or convert
missing evidence into a pass.

## Fresh baseline failures

| Area | Current run | First meaningful failure | Ownership / disposition |
| --- | --- | --- | --- |
| Deployment / Kind | [41141189205](https://github.com/Jagadeeshck/DataObs/actions/runs/41141189205) | API CrashLoopBackOff; runtime import fails with `ModuleNotFoundError: No module named 'integrations'` | Team 0 shared API image packaging. Fix in this branch. |
| MVP | [41141190066](https://github.com/Jagadeeshck/DataObs/actions/runs/41141190066) | API container is unhealthy for the same missing `integrations` package | Team 0 shared API image packaging. Fix in this branch. |
| Main CI | [41141189164](https://github.com/Jagadeeshck/DataObs/actions/runs/41141189164) | Python Black: one Team 0 file plus two Team 2 files; live certification API health failures; Kafka migration alias collision; generic summary invokes Data Product-only manifest builder | Mixed. Team 0 fixes its file, API packaging, Kafka startup ordering, and generic summary. Team 2 files remain Team 2-owned. |
| Foundation | [41141189220](https://github.com/Jagadeeshck/DataObs/actions/runs/41141189220) | Backend Black repeats the same three Python files; Console Prettier fails `src/styles/global.css` | Team 0 formats only its release test. Team 2 owns its two Python files. Team 5 owns Console CSS. |
| Team 2 E2E | [41141189113](https://github.com/Jagadeeshck/DataObs/actions/runs/41141189113) | DataObs API never becomes healthy because the shared API image lacks `integrations`; evidence is then absent | Team 0 runtime dependency is fixed here; Team 2 owns its follow-on exact-SHA rerun/evidence. |

## Shared root causes and repairs

### API image composition

`Dockerfile.api` copied `src/`, `packages/`, and `services/` but not
`integrations/`. API startup imports the stream reliability repository through
`services.kafka_observer`, whose service module imports
`integrations.kafka.admin_client`. Kind, MVP, Team 2 E2E, and the focused
certification API therefore crashed before readiness.

Repair: package `integrations/` in the production API image. Readiness probes
and timeouts remain unchanged.

### Kafka certification bootstrap ordering

The Kafka observer wrote to stable `*-write` aliases before released migrations
created those aliases. Elasticsearch therefore auto-created
`dataobs-kafka-clusters-v1-write` as a concrete index. Migration 0004 then
correctly failed with `invalid_alias_name_exception` rather than replacing it.

Repair: initial certification Compose startup excludes the observer. The existing
Kafka seed/wait step starts it explicitly only after released migrations have
been applied. No released migration or Team 1 storage contract is edited.

### Generic certification summary

The generic CI summary downloaded heterogeneous certification artifacts but
called the Data Product-specific `build_manifest.py` /
`verify_artifacts.py` profile contract. That correctly failed because
`DATA_PRODUCT_CERTIFICATION_PROFILE` was absent; setting a Team 2 profile would
misclassify unrelated evidence.

Repair: use a dedicated generic CI aggregate manifest. It fails closed on
required job conclusions, missing/empty required artifacts, non-clean JUnit,
unredacted sentinels, exact SHA/run attempt, and SHA-256 digest changes.

## Cross-team blockers

- **Team 2 — PR #335:** owns formatting of
  `scripts/certification/verify_team2_sprint4_e2e.py` and
  `tests/integration/data_products/test_migrations_elasticsearch.py`, plus the
  Team 2 exact-SHA E2E/evidence rerun.
- **Team 5 — PR #334:** owns Prettier repair for
  `ui/dataobs-console/src/styles/global.css` and Console quality/browser rerun.
- **Team 3 — PR #336:** separate incident Elasticsearch cleanup verification;
  consume only after it is integrated and exact-SHA certification is rerun.

Team 0 must rebase/re-evaluate after required domain fixes merge. Historical
passes from other SHAs are not sufficient for Gate 0.

## Baseline controls already green on audited main

At `eb9dff57820b39c3dd33a98f834498c30f644d89`, the dedicated Team 0
backup/restore, Team 0 security hardening, and IAM/OIDC/tenant-security workflows
are successful. Migration/OCC, Terraform/Helm, Compose validation,
documentation truth, certification contracts, and production image SBOM checks
also pass in the main CI run where they execute independently.

These are baseline observations only. They must remain green on the final
integrated candidate SHA before Gate 0 can become green.

## Exit conditions

1. Merge only focused shared infrastructure repairs that reproduce.
2. Integrate required Team 2/Team 5/domain closures.
3. Re-run mandatory Gate 0 producers on one exact integrated SHA.
4. Run the canonical Gate 0 verifier and require `GATE_0_GREEN`.
5. Dispatch the canonical Beta capability manifest on that same SHA and
   independently verify run attempts, retained artifacts, digests, mandatory
   suites, Elasticsearch 9.5.5, and terminal migration identity.
6. Freeze `0.2.0-rc.1` only after all mandatory evidence passes.
7. Run protected supported-platform, security, SBOM/provenance/signature, and
   independent release verification.
8. Publish `v0.2.0` only after the formal release authority returns GO.
