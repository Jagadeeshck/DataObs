# PR #115 Data Product 360 follow-up

PR #115 is present in local history as merge commit `487d473`. The checkout has no Git remote or
GitHub review API, so review-thread text, hosted run IDs and hosted artifacts cannot be fabricated.
Release readiness therefore remains **blocked**, the pull request must remain draft, and RCA remains
the next milestone only after the remaining productization gates are evidenced.

| Finding/gap | Root cause | Fix | Test | Hosted job | Evidence |
|---|---|---|---|---|---|
| Strict mappings | Released generic mapping omitted writer fields | Forward-only `0015` installs resource-specific strict fields and verifies incompatible types before success | `test_0015_is_forward_only_and_writer_mappings_are_explicit` | `data-product-contracts` | Local only; hosted pending |
| SLO identity | Evaluation hash omitted tenant, environment, product, method and evidence | Scoped v2 hash and scoped fields in the evaluation document | `test_slo_evaluation_identity_is_scoped_and_corrected_evidence_is_new` | `data-product-elasticsearch` | Local only; hosted pending |
| Event ordering | Service mutated current state before revision evidence | Immutable pending operation is created before OCC mutation; immutable applied outcome follows | `test_pending_operation_is_durable_before_current_state` | `data-product-unit` | Local only; hosted pending |
| Readiness | Decisions resource was absent and checks only tested existence | Decisions are required; diagnostics cover existence, write alias, strict mapping and write blocks | integration partial-migration gate pending | `data-product-elasticsearch` | Hosted pending |
| Repository completeness | PR #115 implemented only product current state and revisions | Operation persistence, create-only outcomes, fixed resources and no routine forced refresh added; remaining workflow persistence is open | repository integration suite pending | `data-product-elasticsearch` | Hosted pending |
| Membership | Proposal/decision production operations incomplete | Not promoted; durable workflow remains open | membership suite pending | `data-product-unit` | Hosted pending |
| SLO persistence | Definition/evaluation repository and application service incomplete | Identity corrected; full persistence/service remains open | SLO service suite pending | `data-product-elasticsearch` | Hosted pending |
| Reliability | Helper exists without complete durable current/history persistence | Not promoted | reliability replay suite pending | `data-product-elasticsearch` | Hosted pending |
| Coverage | Domain contract exists without complete production persistence | Explicit mapping added; workflow remains open | coverage suite pending | `data-product-elasticsearch` | Hosted pending |
| Impact | Domain contract exists without complete bounded repository query | Explicit mapping added; workflow remains open | impact bounds suite pending | `data-product-security` | Hosted pending |
| API | Typed Data Product routes absent | Open | API contract suite pending | `data-product-contracts` | Hosted pending |
| OpenAPI/client | Routes absent, therefore generation cannot be complete | Open | generated-artifact check pending | `data-product-contracts` | Hosted pending |
| Console | List and Product 360 absent | Open | component tests pending | `data-product-browser` | Hosted pending |
| Browser/axe | No journeys for this vertical | Open | Playwright/axe pending | `data-product-browser` | Hosted pending |
| Security | Threat inventory omitted scoped SLO and partial migration attacks | Threat model expanded; executable full matrix remains open | security suite pending | `data-product-security` | Hosted pending |
| Hosted CI | No run is accessible from this checkout | Do not claim validation until a real run URL, SHA, conclusions and hash-verified artifacts exist | summary manifest pending | `data-product-summary` | Hosted pending |

## Mapping scope and rollback

Migration `0015_data_product_360_productization` depends on `0014`, creates no replacement resource,
and only adds mapping properties. Existing documents are retained. The registry compares existing
types (including nested properties), refuses incompatible mappings, and records migration success
only after mapping verification. Rollback stops writers and retains additive mappings and immutable
evidence; it does not pretend Elasticsearch can remove an in-place field mapping.

## Required release statement

> This PR closes the PR #115 correctness findings and completes the Data Product API and Product 360 product surface. It does not complete explainable RCA, Job and Run Explorer, enterprise IAM, autonomous remediation, or DataObs production readiness.

That statement is the target PR scope, not a claim that all gates in this incomplete local follow-up
have passed. Release readiness remains **blocked**.
