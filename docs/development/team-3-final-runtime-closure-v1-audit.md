# Team 3 final runtime closure v1 audit

## Preflight

The audited supplied `main` snapshot is `d4f511ebb331b74528426b91ce69bd24f8993eac` (merge PR #244, the
latest merge by commit date in the supplied history). `python scripts/release/current_terminal_migration.py`
reported `0030_team1_multi_broker_messaging_runtime`. The checkout has no `origin` remote and GitHub's private PR
API returned 404 without credentials, so remote fetch and comment retrieval could not be completed. Local merge
commits/diffs for PRs #219, #230, #235, #241, #247, and every supplied merge after #247 (#248, #249, #246, #245,
and #244 in repository topology) were inspected. The six Codex findings carried by the PR #247 task are audited
below; no claim is made that inaccessible remote-only discussion was read.

## PR #247 findings

| PR #247 finding | Severity | Reproduced on latest main | Root cause | Fix | Test | Status |
| --- | --- | --- | --- | --- | --- | --- |
| A listed authoritative target cannot be selected | P1 | Yes | Preview always returned `selection_required` and accepted no bounded handle | Expiring signed handle binds scope, action, incident, candidate identity and resolution generation; resubmission re-resolves and reloads | `test_server_candidate_selection_can_proceed_and_is_scope_bound`, arbitrary/stale test | Closed |
| Executor return can race its deadline | P1 | Yes | Only heartbeat checked the deadline | Main thread captures completion independently; `finished_at > deadline` enters reconciliation with bounded evidence and no provider response | `test_late_executor_result_cannot_commit_success_and_requires_reconciliation` | Closed |
| Batch items share execution start | P1 | Yes | `run_once` reused its queue-query timestamp | Claim and execution start use fresh per-item clock values | `test_each_batch_item_gets_own_execution_start_and_full_timeout` | Closed |
| OpenAPI requires rejected execution revisions | P1 | Yes | Generated artifact was stale | Repository generator regenerated the schema; execution input is `preview_id` plus optional `approval_id` only | generated-artifact check and schema assertion | Closed |
| Incident targets use capability authority | P1 | Yes | Resolver only dispatched scanner/monitor/integration | Static registry routes incident to the incident repository and fails unknown types closed | `test_incident_target_uses_incident_repository_and_bypasses_capability_reader` | Closed |
| Case searches sort on Elasticsearch `_id` | P1 | Yes | `_id` was used as a tie-breaker | Searches use mapped `updated_at` and scoped deterministic `incident_id`; exact link IDs already use GET | `test_case_repository_never_sorts_on_id_and_sort_is_deterministic` | Closed internally; real ES not run |

## Runtime contracts

Selection handles contain no secrets. They are authenticated by the shared signed-cursor codec, expire after five
minutes, and bind tenant, environment, incident, action, target type/ID, and a hash of the complete bounded candidate
generation. The server resolves candidates again, verifies membership, and reloads the selected target revision.
Browser target IDs and revisions never establish authority.

Provider timeout begins independently for every batch item immediately before `RUNNING`. Exact deadline equality is
allowed; a completion strictly later than the deadline is uncertain and becomes `reconciliation_required`. The
normal provider result and operation reference are discarded. Repository fencing remains mandatory on the final
write.

Incident targets derive `seq_no:primary_term` from the scoped durable incident projection. Scanner, monitor, and
integration targets continue through their capability owners. Unknown target types have no authority.

Case link exact document identity uses Elasticsearch GET. Searches always include tenant, environment, and Kibana
space predicates and sort by mapped fields only. The optional `search_after` tuple is exactly the two-field sort
tuple; API clients cannot supply Elasticsearch query or sort DSL. No mapping migration was required.

`src/api` models are the OpenAPI source of truth. `scripts/generate_openapi.py` regenerated `openapi.json`; current
execution requests require only `preview_id`, never incident or target revisions.

## Migration and certification

Starting and ending terminal migration: `0030_team1_multi_broker_messaging_runtime`. Migration added: no. Released
migrations modified: no. Elasticsearch 9.4.2, Kibana 9.4.2, Playwright, and axe certification were not run because a
hosted stack and credentials were not available; no real-stack pass is claimed.
