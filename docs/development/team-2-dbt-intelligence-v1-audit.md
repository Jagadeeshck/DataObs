# Team 2 dbt Intelligence v1 audit

- **Codex title:** Team 2 — Build dbt Project, Test and Semantic Intelligence v1
- **PR title:** Team 2: Build dbt Project, Test and Semantic Intelligence v1
- **Owner:** Team 2 — Data Quality, Jobs and Lineage
- **Audited base:** `d4f511ebb331b74528426b91ce69bd24f8993eac`; **final SHA:** populated by Git/PR after commit.
- **Migration:** terminal `0030_team1_multi_broker_messaging_runtime`; decision: no migration because Elasticsearch persistence is not production-certified.
- **Artifacts/schemas:** manifest v7–v12, run-results v4–v6, catalog v1, sources v2–v3; schema URI and dbt version are mandatory.
- **Parser:** one canonical safe parser under `integrations/dbt`; Change Gates is a thin wrapper.
- **Identity/integration:** scoped deterministic resource/asset/run IDs; canonical Jobs/Runs, Lineage, Contracts, monitoring/findings and Data Products are reused rather than duplicated.
- **Intelligence:** typed models/sources/seeds/snapshots/tests/unit tests/exposures/groups/semantic models/metrics/saved queries; bounded execution/freshness/catalog evidence; explainable flaky detection, semantic coverage, lineage reconciliation and health.
- **API:** authenticated `/api/v1/dbt` ingestion/project/resource/test/semantic/freshness foundation with permission policy and trusted tenant context.
- **Security:** restricted fields rejected, adapter messages omitted, stats allowlisted, bounds enforced, tenant isolation tested.
- **Tests:** focused Python tests cover schema rejection, artifact families, resource families, unsafe fields, limits, idempotency, isolation, health, flaky/consistent tests, lineage and Change Gate consolidation.
- **Elasticsearch/UI/browser/accessibility:** not certified in this local increment; no production-ready claim. No index/migration or Console page was introduced.
- **Performance:** streaming/PIT Elasticsearch evidence for 100k resources/500k results is not yet measured; parser inputs and returned lists are bounded.
- **Workflow/evidence/independent verification:** hosted evidence does not yet exist; capability remains blocked and uncertified.
- **Rollback:** revert the feature commit; no migration or irreversible persistence operation exists.
