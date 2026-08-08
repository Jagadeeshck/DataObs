# Elastic Cases and Workflows integration v1 audit

## Preflight

* **Audited SHA:** `70f77d85b17776fe2222d591788f145269479057` (local merge of PR #229; it contains PR #230).
* **Terminal migration:** dynamically reported as `0027_platform_environment_tenant_multicluster_lifecycle` before changes.
* **History reviewed:** local merge commits/diffs for PRs #187, #202, #209, #217, #219, #230 and later available Team 0/Team 5 merges. GitHub review-comment retrieval was attempted with `gh pr view 230 --comments`; the environment has no GitHub credential, so the audit is limited to merged code, commit history, and the existing PR #230 closure audit.
* **Target:** Elasticsearch/Kibana 9.4.2. Documentation lookup was attempted but the documentation search service returned HTTP 401. Selected GA endpoints follow the pinned contract: create `POST /api/workflows/workflow`, read/update `/api/workflows/workflow/{id}`, run `/api/workflows/workflow/{id}/run`, execution `/api/workflows/executions/{executionId}`, and inventory `/api/workflows/workflow/{workflowId}/executions`. Cancellation is not enabled because its exact contract could not be independently certified.

The prior Workflow client exposed a generic path request, followed redirects, returned response text in errors, used 9.3-style paths/import, and mixed credentials. The prior deployer only validated/printed a pack. Execution sync copied statuses and provider structures without an explicit compatibility map. No production Case client/service existed.

## Storage audit and migration decision

Existing manifest resources are `dataobs-case-links-v1`, `dataobs-workflow-definitions-v1`, `dataobs-workflow-bindings-v1`, `dataobs-workflow-executions-v1`, `logs-dataobs.workflow_execution-*`, `logs-dataobs.workflow_step-*`, `logs-dataobs.remediation_action-*`, plus incident timeline resources. Strict envelopes with bounded flattened metadata support this foundation. Starting and ending terminal migration remain `0027_platform_environment_tenant_multicluster_lifecycle`; no released migration was edited.

## PR #230 closure audit

| Review finding | Severity | Reproduced | Fix | Test/evidence | Status |
| --- | --- | --- | --- | --- | --- |
| Authoritative target resolution | P1 | Yes: evidence-only resolver remains | Finding and target repository interfaces are required | Limitation documented | **Open blocker** |
| Pending evidence coupled to leases | P1 | Yes | Bounded pending lookup, deterministic create-only append and fenced clear for every state | Repository/reconciler tests | Closed |
| Failure transitions lack evidence | P1 | Yes | Bounded deterministic descriptor/event without exception text | Worker tests | Closed |
| Current revisions server-side | P1 | Partial | No unsafe client authority added; authoritative target repository is absent | Limitation documented | **Open blocker** |
| Policy identity incomplete | P1 | Yes | Canonical structured decision definition and derived hash | Policy hash regression | Closed |
| Preview scans first 100 | P1 | Yes | Generation-descending query, size one, deterministic collision | Query regression | Closed |
| Running lease heartbeat | P1 | Yes | Not implemented; safe independent heartbeat requires worker lifecycle changes | Limitation documented | **Open blocker** |

This is a production-safe bounded foundation, **not certification of the full mission definition of done**. The three open Phase 0 blockers must be closed before provider mutations are enabled; flags remain off by default.

## Selected architecture

One shared bounded Kibana transport owns origin, TLS/redirect/timeout/response limits, XSRF, safe errors, correlation and explicit endpoint builders. Environment-to-space mapping is server-owned. Logical credentials are separate: Cases runtime (Case read/write), Workflow deployer (create/read/update), and Workflow runtime (read/run/execution-read).

Cases use Observability ownership and connector none. The scoped deterministic reference is the reservation/link ID and remote tag. States are `unlinked → create_reserved → linked`, with `create_reconciliation_required` after uncertain response. Inbound status is collaboration state only.

The initial workflow is `dataobs-incident-case-triage-v1`. Allowed steps are `cases.getCase`, `cases.addComment`, and `cases.addTags`. Generic HTTP, `kibana.request`, shell/script/exec, unknown steps, Case delete/push, credentials and deprecated aliases are forbidden. Exact executions are polled without input/output. Status mapping covers pending, waiting, waiting-for-input, running, completed, failed, cancelled, timed-out and skipped; other values are `provider_status_unknown`.

## Remaining gaps

Authoritative target resolution/reload, execution heartbeats, Elasticsearch Case-link persistence, uncertain-create remote reconciliation, Safe Remediation Case/Workflow executors and bindings, APIs/UI, telemetry, cancellation certification, hosted browser/accessibility evidence, and licensed 9.4.2 real-stack certification remain.
