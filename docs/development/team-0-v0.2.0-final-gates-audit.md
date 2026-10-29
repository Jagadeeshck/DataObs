# Team 0 v0.2.0 final gates audit

Assessment date: 2026-10-29.

## Audited integrated baseline

- Starting `main`: `8115f557ad7f6c53ab73054dc356f7bbfb676054`
- Task branch: `codex/v020-team0-final-gates`
- Release target: `0.2.0-rc.1`
- Release decision at start: `NO_GO`
- Candidate frozen at start: no
- Supported platforms at start: none
- Executable terminal migration at audited baseline: derive with `scripts/release/current_terminal_migration.py`; the preceding release baseline reported `0033_team1_stream_schema_intelligence_runtime`.
- Historical evidence is diagnostic only. No PR-head or earlier-main artifact is promoted to this branch.

## Integrated changes reviewed before Team 0 edits

The baseline includes release-stabilisation work from Teams 0–5, including Team 2 PR #322 and Team 5 PR #321. Team 2 added authenticated tenant/environment scoping for legacy rule and quality-result storage. Team 5 added the final Console formatting/browser-certification corrections. Those source changes require fresh exact-SHA execution before Gate 0 can consume them.

## Latest meaningful hosted failures reviewed

The latest executed Team 2 head `b80178abe95a2cb18983df1ea06555685ea9beb2` exposed the next shared clean-install failure:

```text
RuntimeError: Incompatible existing mapping on
dataobs-reliability-status-v1: observed_value
```

Observed producers affected by this shared failure included Team 0 security hardening, First MVP smoke, deployment migration startup and Data Product Elasticsearch/security certification.

The prior Data Product `dataobs-data-products-v1` and `dataobs-data-product-revisions-v1.revision` conflicts are not assumed current after the integrated fixes; they must be re-tested rather than repaired again.

## Root cause: reliability mapping ownership

`packages/elastic_store/registry.py::_mapping(index)` creates mutable indices from a broad global property union. The registry previously overlaid explicit ownership for incident and Data Product indices only. `INCIDENT_AUTOMATION_PROPERTIES` defines `observed_value` as `flattened`, while released migration `0025_stream_pathway_reliability_production_closure` explicitly requires `dataobs-reliability-status-v1.observed_value` to be `double`.

A clean install therefore created the concrete reliability index with the global-union type before migration 0025 verified its released contract. Migration validation correctly failed closed.

Disposition: `TEAM0_MIGRATION_PLATFORM`.

Repair on this branch: initial concrete-index creation now overlays the first released explicit `mapping_updates` definition for every field of every concrete index. Later mapping updates remain fail-closed. No released migration definition or checksum is edited. A regression walks every released mapping target and verifies clean-index creation preserves those first released field definitions.

## Tenant isolation

Earlier hosted runs proved a real legacy `/rules` cross-tenant list/search/delete defect. Team 2 PR #322 has since changed source to scope legacy stores by authenticated tenant/environment and added regression coverage.

Disposition on this branch: `SOURCE_FIXED_HOSTED_PROOF_PENDING`.

The Gate 0 OIDC/tenant tests remain enabled. No xfail, skip, selector bypass or permission weakening is introduced. Both memory and Elasticsearch-backed behaviour require hosted/focused proof before the security gate may pass.

## Console/browser

Earlier Team 5 heads failed Prettier before Playwright. Team 5 PR #321 contains formatter fixes and strengthened hosted browser evidence validation.

Disposition on this branch: `SOURCE_FIXED_HOSTED_PROOF_PENDING`.

Team 0 does not edit Team 5 product assertions. This branch changes only release orchestration: Console Beta now emits the canonical exact-SHA evidence envelope and becomes an explicit Gate 0 producer requiring both browser and accessibility categories.

## Supply chain

The shared CI already has `Production image security and SBOM`. It was not a dependency of the canonical shared Gate 0 evidence job and was not an explicit required job in the Gate 0 manifest.

Disposition: `TEAM0_RELEASE`.

This branch makes that job a dependency of `Mandatory Team 0 Gate 0 evidence` and a required job in the Gate 0 manifest. Missing/failed image-security/SBOM evidence therefore prevents Gate 0 GREEN.

## Recovery

The audited source already sets both the global integration opt-in and the bounded destructive-recovery opt-in in `beta-backup-restore.yml`, writes semantic JSON/JUnit, validates executed evidence and produces the canonical envelope.

Disposition: `SOURCE_FIXED_HOSTED_PROOF_PENDING`.

No recovery PASS or timing is claimed until the hosted destructive test executes for the final exact SHA.

## Gate 0 release truth

Current branch source is not a certified release candidate. The branch must rerun all canonical Gate 0 producers on one exact final SHA, retain their canonical evidence, and pass `scripts/release/gate0.py verify`.

Until that occurs:

- Gate 0: `GATE_0_BLOCKED`
- release decision: `NO_GO`
- candidate frozen: false
- supported platform: none

Any subsequent source fix changes the candidate SHA and invalidates earlier branch evidence for final Gate 0 aggregation.
