# Team 2 v0.2.0 release readiness audit

**Team:** Team 2 — Data Quality, Job Observability and Lineage  
**Branch:** `codex/release-team2-quality`  
**Starting main:** `09fa1fe615c69f79a8056772a4b424b5c564fb86`  
**Target:** DataObs `v0.2.0`

This audit records observed hosted evidence and the focused Team 2 fixes. It does not authorize a release and does not promote any capability without final-head evidence.

## Initial failure classification

| Workflow | Observed hosted result | Classification | Team 2 disposition |
| --- | --- | --- | --- |
| `data-quality-monitoring.yml` | Domain/ES/PostgreSQL/tenant/RBAC certify job passed; independent verifier could not find `metadata.json` | Team 2 certification packaging defect | Fix artifact root; rerun exact head |
| `data-quality-console-v1.yml` | Backend/static/unit/build passed; full shared Playwright suite failed | Shared Console/browser blocker | Keep Quality behavior unchanged; Team 5 owns shared shell/browser defects |
| `job-run-backend.yml` | OpenLineage/projection/tenant/RBAC certify job passed; independent verifier could not find `metadata.json` | Team 2 certification packaging defect | Fix artifact root; rerun exact head |
| `lineage-analysis-console.yml` | Lineage traversal/cycle/truncation/backend/build passed; full shared Playwright suite failed | Shared Console/browser blocker | Keep Lineage behavior unchanged; Team 5 owns shared shell/browser defects |
| Data Product hosted certification | Unit/contracts passed; clean-install migration application rejected `dataobs-data-products-v1` field types | Data Product clean-install mapping defect in shared storage code | Preserve released migrations; create the index with the owning Data Product mapping; Team 0 review required |
| Data Product reconciliation certification | Unit/contracts passed; same migration apply blocker | Same clean-install mapping defect | Same focused correction |
| Team 2 Data Reliability SLO | Tests did not start: `pytest: command not found` | Team 2 workflow bootstrap defect | Install canonical `requirements-ci.txt` |
| Team 2 data-intelligence reconciliation | Guards passed; tests did not start: `pytest: command not found` | Team 2 workflow bootstrap defect | Install canonical `requirements-ci.txt` |

## Focused corrections

- Package each Team 2 certification artifact from one evidence directory and download it into the exact verifier directory. Do not mix absolute `/tmp` paths into the evidence archive.
- Install runtime plus canonical CI requirements in the SLO and data-intelligence reconciliation workflows.
- Preserve the Data Product-owned field mappings for `dataobs-data-products-v1` during clean installation so migration 0015 validates rather than conflicts.
- Add a regression test for `description`, `owner`, `revision`, and `tags` mapping ownership.
- Do not edit migration 0007, 0015, or any other released migration.

## Core feature acceptance matrix

| Capability | Domain evidence at starting head | Final-head requirement |
| --- | --- | --- |
| Monitor creation/configuration | Existing focused Quality tests | Pass |
| Schedules/checkpoints/evaluations | Existing monitor runtime tests | Pass |
| Baseline and quality rules | Existing monitor tests | Pass |
| Missing/stale/zero/error semantics | Existing focused Quality tests | Pass with measured-zero preserved |
| Manual run-now safety | Existing bounded lifecycle behavior; verify explicitly | Pass before promotion |
| Quality → OTel/collector → ES → finding → deduplicated incident | Focused Quality JUnit includes the integration test as an environment-gated skip; the complete compose-backed path is executed by `CI / Integration tests` with `RUN_INTEGRATION_TESTS=1` and emits `e2e-signal-path` | Final-head `e2e-signal-path` artifact must pass; the focused skip is not E2E proof |
| OpenLineage ingestion/validation | Job certify job passed at starting head | Exact-head pass + independent verification |
| Job/Run projection and isolation | Job certify job passed at starting head | Exact-head pass + independent verification |
| Lineage cycles/truncation/partial evidence | Lineage backend suite passed at starting head | Exact-head pass |
| Data Reliability SLO formulas | Implementation exists; workflow bootstrap prevented test execution | Exact-head pass |
| Data Product reliability/reconciliation | Unit/contracts passed; clean-install mapping blocked ES jobs | ES 9.4.2 clean-install/repeat/upgrade pass |
| Console Quality/Lineage journeys | Shared Playwright suite currently red | Team 5 coordinated final-head browser/axe pass |

## Cross-team boundaries

### Team 3

Team 2 owns the quality evaluation/finding evidence that feeds the incident boundary. Team 3 retains incident lifecycle, deduplication, correlation and automation ownership. Team 2 must not introduce a second incident engine or weaken deduplication semantics.

### Team 5

Team 2 owns Quality/Jobs/Lineage product behavior. The observed browser failures include shared shell, supportability and Data Product journeys and therefore are not evidence of a Quality or Lineage domain failure by themselves. Team 5 owns the shared Console harness/shell remediation and final browser/accessibility certification.

### Team 0

The Data Product clean-install fix touches the shared Elasticsearch registry but does not change a released migration or relax mapping validation. Team 0 review is required before merge.

## Release exclusions until proven

- No production-ready claim based on local/unit results alone.
- No browser or accessibility certification while the shared Playwright suite is red.
- No Data Product ES certification until clean-install, repeat apply and reconciliation pass on Elasticsearch 9.4.2.
- No SLO certification until the focused tests actually execute.
- No evidence promotion unless the independent verifier accepts the final-head artifact.\n- The focused Quality workflow must not be cited as end-to-end signal-path proof while its container-backed test is skipped; use the exact-head `e2e-signal-path` artifact from CI.
- No autonomous remediation, new quality engine, new connector, or migration rewrite.

## Success condition

A pilot workflow is accepted only when the final integrated SHA proves that a tenant-authorized user can investigate a Quality or Job failure through canonical evidence, retrieve the related lineage/reliability context, and follow the quality finding into the existing deduplicated incident boundary without converting missing evidence to zero or bypassing authorization.
