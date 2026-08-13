# Team 2 data-quality SLO v1 preflight

Date: 2026-08-13. Base and latest locally available `main`: `141ec426bef2f168996df122655b9bf2cb395ff7`. The checkout has no configured remote, so fetch/pull could not advance or independently verify that SHA. Terminal registered migration is `0030_team1_multi_broker_messaging_runtime`; released checksums are recorded in `docs/product/capability-ledger.yaml` and were not edited.

## Existing ownership and reuse

* `packages/domain_model/data_product.py`, `services/data_products/slo.py`, and `services/data_products/slo_evaluator.py` already define bounded Data Product component objectives, deterministic evaluation identity, coverage, confidence, and lifecycle. They remain backward compatible.
* `services/data_products/reliability.py` owns weighted product reliability. Membership and dependencies are canonical Data Product scope inputs.
* `services/monitoring` and `services/monitor_runtime` own monitor evidence and scheduling. `services/job_reliability` owns expected/missing/late run semantics. `services/data_contracts` owns contract evaluation. SLO evaluation must consume, not repeat, these decisions.
* `services/dbt_intelligence` owns dbt tests/freshness/model evidence. `services/lineage_intelligence` owns bounded downstream enrichment. `services/change_gates` owns whether SLO context warns or blocks.
* Existing canonical findings are the alert boundary; Team 3 owns incident lifecycle. Asset identity remains the canonical domain identity rather than an SLO-local ID.
* Existing API SLO routes are Data Product reliability routes; Console quality routes are registered centrally in `ui/dataobs-console/src/app/routes.ts`. This slice does not introduce a conflicting route.
* Capability `monitoring.products` owns existing Data Product SLOs. The distinct Team 2 capability is asset/job data-reliability semantics that can roll into that capability.

## Decision

Add canonical common contracts and arithmetic at `packages/domain_model/slo.py`, then let existing Data Product evaluation consume child evaluations. Do not create `quality_slo_v2`, re-run contract rules, inspect raw rows, or use stream/platform SLO stores. No migration is justified for this foundational slice because no production repository writer/reader is introduced; adding unused indices would violate the resource rule.
