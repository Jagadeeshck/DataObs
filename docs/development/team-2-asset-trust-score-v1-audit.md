# Team 2 — Asset Trust and Reliability Score v1 audit

- **Codex/PR title:** Team 2 — Build Asset Trust and Reliability Score v1 / Team 2: Build Asset Trust and Reliability Score v1
- **Team:** Team 2 — Data Quality, Jobs and Lineage
- **Base:** `39b7757`; **final SHA:** recorded by Git after commit; **terminal migration:** `0032_team2_data_slo_production_runtime`
- **Existing reliability reviewed:** Data Product, Data SLO, job, dbt, monitoring, schema, lineage, contract, and stream implementations.
- **Model:** asset-only score (0–100), independent confidence and coverage (0–1), eight bounded dimensions, provenance, immutable policy-versioned history, deterministic identity.
- **Policy:** weights 20/15/15/20/10/5/10/5; required quality/freshness; minimum confidence 0.60; declarative thresholds and high-confidence caps only.
- **Formula:** eligible weighted mean; coverage = weighted availability; confidence = coverage × freshness × source-confidence. Missing is excluded, all missing is unknown, required missing/low confidence is partial, stale evidence lowers confidence.
- **Caps:** contract critical violation 60, exhausted SLO 65, critical freshness 50; uncapped/final values and reason are retained.
- **Overlap:** production SLO > canonical domain > canonical evaluation, with `derived_from` claims preventing monitor/SLO, dbt/canonical, and job/SLO duplication.
- **Integrations:** canonical quality/freshness/SLO/contract/job/dbt/schema/lineage/ownership evidence is accepted; source engines are not recreated. Criticality, downstream impact, Data Product member context, and Change Gate context remain separate from score calculation.
- **Repository/security:** memory and Elasticsearch implementations scope tenant/environment, offer policy OCC, idempotent append, current/history/inventory/bulk/health operations, and never store raw rows.
- **Runtime/API/Console:** scoring service and storage contract are implemented; worker wiring, signed-cursor HTTP endpoints, `/quality/trust`, Asset 360 integration, and contextual consumers remain limitations.
- **Elasticsearch/migration:** ES repository targets 9.x APIs. No migration was added without latest-main reconciliation; ES 9.4.2 apply/repeat/upgrade/restart tests remain required.
- **Scale/browser/axe:** not certified in this snapshot. No throughput or accessibility claim is made.
- **Workflow/artifact/independent verification:** not certified; capability must remain unvalidated and must not be promoted.
- **Rollback:** stop callers, revert application commit, and retain immutable evaluation history. Remove resources only through a separately reviewed forward migration after retention review.
