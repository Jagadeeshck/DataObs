# Team 2 data SLO production closure preflight

## Reconciliation record

* **Codex title:** Team 2 — Production-Close Data Quality SLOs, Error Budgets and Burn Rate Intelligence v1
* **Audited base:** `96d6e4fc0e20d11ee7dcaca5f681660d5dd2be52` (the supplied checkout has no Git remote, so this is the newest locally auditable main-equivalent).
* **PR #260 dependency:** merge `294851860826cf024ab41899c6cc8d5af6778c81`.
* **Terminal before:** `0031_team3_post_incident_review_analytics`, checksum `95ebe301e7d43f7dc68668e0d8295654814c1bfe67e5d001a67d6dbb755c8f3b`.
* **Released sequence:** `0001` through `0031`, contiguous. The pre-change manifest SHA-256 is `235e0e83cd9bb82c5c58c42031cbd25afc262b9ad0dc8c73ba8be8637abd4330`.

## What #260 delivered

`packages/domain_model/slo.py` is authoritative for definition/evaluation contracts, four-way interval classification, three missing-evidence policies, deterministic evaluation identity, budget and multi-window burn. `services/data_products/slo.py`, `slo_evaluator.py`, and `reliability.py` consume those contracts for evidence-honest roll-up. No formula is changed by this closure.

## Gaps confirmed

There was no definition/evaluation repository, SLO runtime projection, fenced scheduler, typed SLO API, or SLO Console. The existing documents and workflow describe the domain-only delivery. The capability ledger correctly remains `functional_unvalidated`.

## Reused foundations

The review covered monitor definition/evaluation repositories and runtime leases; Job/Run Reliability; Data Contract and dbt Intelligence services; bounded Lineage Intelligence; Change Gate services; canonical Data Product and Finding models; strict mappings in `packages/elastic_store/manifest.py`; `SignedCursorCodec`; monitor/Data Product ETag patterns; current quality routes and Console route registry; capability ledger, generated feature matrix, evidence index, and ownership records. Production orchestration must consume those canonical outputs rather than call providers or repeat their evaluators.

## Decision

Add one forward-only `0032` migration and a `services.data_slo` orchestration layer. Historical migrations remain byte-for-byte unchanged. Elasticsearch/browser/certification results remain unvalidated until hosted exact-head evidence exists; no production certification claim is made.
