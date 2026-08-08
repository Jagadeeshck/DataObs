# Elastic Cases and Workflows production runtime v1 audit

## Preflight

The audited local `main` snapshot is `5be28cb2d6f3b3294e7bd0a511d08d5c7bdc2074`. The checkout had no
configured remote; a fetch of `https://github.com/Jagadeeshck/DataObs.git` was attempted on 2026-08-08 and
failed because the repository requires credentials. Consequently this change is based on the newest supplied
local main snapshot and must be rebased by the maintainer if upstream advanced. The dynamically reported terminal
migration is `0028_pathway_investigation_history`; no migration is changed by this work.

Local merge history and patches for PRs 187, 202, 209, 217, 219, 230, 235, and locally available merges after
235 were reviewed. GitHub review/API access and Elastic's online API documentation both returned authentication
errors. The complete PR 235 patch and its audit were inspected locally. The pinned contract therefore remains the
Kibana 9.4.2 contract recorded by PR 235: Cases create/read/comment/find endpoints and Workflow definition/run/exact
execution endpoints. Workflow cancellation remains disabled. This is not represented as hosted certification.

The existing strict resources were inspected through the migration manifests and mappings: Case links, Workflow
definitions/bindings/executions, action idempotency, Workflow execution/step, remediation action, verification, and
incident timeline streams. Their bounded `flattened` metadata envelopes accommodate the runtime state without a
forward migration. Production adapters serialize explicit storage documents rather than domain models directly.

## Gap closure ledger

| Gap | Current state | Production requirement | Change | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Target authority | Evidence snapshot helper existed | Finding references then owner boundary | Added bounded `BoundedActionTargetResolver` with repository/time/candidate limits and owner reload | `test_normal_incident_resolves_scanner_target`, owner-revision test | Implemented; composition certification pending |
| Ambiguous targets | Exception with evidence candidates | Selection only from server candidates | Structured resolved/selection-required/unavailable result | resolver unit tests | Implemented |
| Current target revision | Incident evidence revision | Reload from owning capability | `reload` always calls owner reader | owner-revision test | Implemented |
| Worker heartbeat | Fixed 60-second lease, no renewal | Independent fenced renewal | Configured lease/heartbeat invariant and daemon heartbeat around blocking execution | fenced renewal test plus baseline runtime tests | Implemented; real ES fault test pending |
| Fence loss | Old worker could final-write after expiry | Reject all stale writes without stopping loop | Heartbeat loss suppresses result/evidence writes; repository verifies owner and token | fenced renewal test | Implemented |
| Case durability | In-memory protocol only | Elasticsearch/OCC production adapter | Added explicit strict-envelope adapter, scoped reads, create reservation, state helpers and reconciliation queries | existing Case tests; hosted ES test pending | Implemented, functional_unvalidated |
| Duplicate Case | Process lock only | Deterministic create-before-provider reservation | ES `create` uses deterministic link id and treats conflict as idempotent only for the same reference | repository contract tests pending real ES | Implemented, functional_unvalidated |
| Uncertain Case create | Reconciliation-required state | Durable reconciliation | State and bounded due query persist uncertainty; no blind retry | service regression | Partially implemented; provider search worker not certified |
| Nested Workflow validation | Top-level only | Recursive composite inspection | Recursive traversal of branches/steps/then/else/sub-workflow containers | `test_nested_unsafe_workflow_step_is_rejected` | Implemented |
| Workflow binding/execution runtime | Foundation only | Durable reviewed binding, drift gate, sync and UI | No safe claim of completion without licensed/provider infrastructure | Existing Workflow foundation tests | Open |
| Real Kibana 9.4.2 | Unavailable | Licensed exact-head run | No credentials or licensed stack in environment | not_run | Blocked externally |
| Browser and axe | Foundation UI only | End-to-end panels and accessibility | Not represented as passed | not_run | Open |

## Safety and operational conclusions

Provider mutation remains disabled by default. DataObs retains incident, approval, execution, verification, recovery,
and audit authority; external Case fields remain collaboration state. Unknown provider outcomes remain
reconciliation-required and must never be retried blindly. Heartbeat configuration requires the interval to be no
greater than one third of the lease, while takeover queries continue to select only genuinely expired leases.

No released migration or checksum was edited. Rollback is code-only: stop the Team 3 worker and restore the prior
application revision; durable reservations and reconciliation-required records must be retained for later repair.
Capability status remains `functional_unvalidated` until independently verified exact-head evidence includes real
Elasticsearch 9.4.2 OCC/concurrency and licensed Kibana Cases/Workflows runs.
