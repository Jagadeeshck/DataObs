# Team 2 — Build Data Quality SLOs, Error Budgets and Burn Rate Intelligence v1 — audit

PR title: **Team 2: Build Data Quality SLOs, Error Budgets and Burn Rate Intelligence v1**. Team: **Team 2 — Data Quality, Jobs and Lineage**. Base SHA: `141ec426bef2f168996df122655b9bf2cb395ff7`; final SHA is recorded by the PR after commit.

The existing-SLO findings and shared-model decision are in the preflight. Shared `DataReliabilitySLODefinition` supports asset, monitor group, job, and Data Product scopes; named freshness, quality, completeness, volume, schema stability, pipeline success/timeliness, contract compliance, and availability families; revision/lifecycle; bounded window/granularity; canonical source IDs; exclusions; and missing/backfill policy. Existing `DataProductSLODefinition` is unchanged for compatibility.

Intervals are good, bad, unknown, or excluded. `partial` is the truthful default; `exclude` and `count_as_bad` are deterministic alternatives. Coverage is known evidence divided by expected intervals. SLI is good divided by policy-eligible intervals. Error budget and burn formulas, zero-budget behavior, state boundaries, and multi-window thresholds are documented in the architecture guides. Historical identity includes revision and an evidence fingerprint. Backfills default to original event-time truth; late evidence must produce a superseding append-only evaluation.

Asset, job, contract, and dbt SLOs consume canonical evidence and never evaluate provider/domain rules. Data Product roll-up consumes child evaluations, deduplicates IDs, reports missing children, and applies a critical-component cap. Change Gates may receive current SLO context but retain policy authority. Findings are canonical and transition-driven. Lineage impact is bounded asynchronous enrichment.

## Delivery status and limitations

This commit delivers and unit-tests the canonical model, interval evaluator, numerical safety, missing-evidence policies, exclusions, burn classification, deterministic identity, and Data Product child roll-up. It deliberately adds no Elasticsearch resources because no production repository is present in this slice. API, OCC repository/runtime, Console, browser/axe, Elasticsearch 9.4.2, scale, hosted workflow artifact, and independent verification remain **not implemented/not run**; therefore capability status remains `functional_unvalidated` and no production-readiness claim is made.

Security contracts bind tenant/environment and prohibit raw evidence. Rollback is to stop callers of the additive shared model and revert this commit; no stored data or migration needs destructive rollback.
