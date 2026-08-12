# Team 2 dbt Intelligence v1 preflight

- **Codex title:** Team 2 — Build dbt Project, Test and Semantic Intelligence v1
- **Audited base:** `d4f511ebb331b74528426b91ce69bd24f8993eac` (the checkout has no `origin` remote or local `main`; the required fetch/pull was attempted and recorded as unavailable).
- **Terminal migration:** `0030_team1_multi_broker_messaging_runtime`; 30 released migrations. No migration is required because v1 uses a bounded repository abstraction and the production Elasticsearch projection is explicitly not claimed.
- **Official schemas:** direct access to `schemas.getdbt.com` was attempted on 2026-08-12 and blocked by the environment proxy (403). The explicit compatibility matrix is manifest v7–v12, run-results v4–v6, catalog v1, and sources v2–v3. This limitation must be re-audited before certification.

## Existing capability audit and reuse

| Area | Existing implementation | v1 disposition |
|---|---|---|
| dbt | `integrations/dbt/normalizer.py`, artifact modules, Cloud and OpenLineage adapters | canonical parser is now `integrations/dbt`; Cloud collection is excluded |
| Change Gates | `services/change_gates/changed_models.py` had its own parser | retained only as a compatibility wrapper |
| OpenLineage | `services/openlineage_ingest` and dbt adapter | runtime edges remain canonical observed evidence |
| Jobs/runs/tasks | `services/job_observer`, `services/job_reliability`, canonical API job/run models | invocation IDs map deterministically; no new run engine/store |
| Asset identity | canonical data-observability assets and tenant/environment scoping | dbt physical resources receive deterministic canonical asset IDs |
| Lineage | `services/lineage_intelligence` repository, provenance and traversal | declared edges are projections; no new graph or traversal |
| Contracts | `services/data_contracts` models/evaluator | dbt contract metadata stays separate; future adapter calls canonical evaluator |
| Quality/findings | `services/monitoring`, monitor runtime and recommender lifecycle | no automatic finding, incident, contract, or monitor mutation |
| Data Products | `services/data_products` dependency and impact services | dbt evidence can be resolved through canonical asset identity; no duplicate product identity |
| Ownership | group/node metadata plus canonical ownership | evidence is displayed without overwriting catalog/CMDB ownership |
| Console | central Jobs, Lineage and Quality routes in `ui/dataobs-console` | API foundation only in this increment; browser surfaces remain uncertified |
| Contracts | generated `openapi.json` and Console generated client | generation is required after API registration |
| Governance | capability ledger, boundary scripts, workflow conventions | capability remains foundation/blocked until hosted evidence exists |

Released migration checksums are governed by `scripts/check_migration_immutability.py`; none were edited. Shared API, routes, generated artifacts, ledger and workflow remain subject to Team 0 checks.
