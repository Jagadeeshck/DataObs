# Incident Workbench v1 implementation audit

Audit baseline: the latest local `main` merge (`97a982c`), verified before implementation. Two requested filenames were not present: the applicable equivalents are `github-delivery-conventions.md` and `shared-contract-rules.md`.

## Verified baseline

* `IncidentManagerService` already normalized and deduplicated findings, calculated severity, enforced the legal lifecycle graph, and used Elasticsearch in production composition. The in-memory repository was the deterministic test implementation.
* The fixed findings and incidents v1 read/write aliases already existed. Released migration `0011` also declares the incident assignment, watcher, task, timeline, action, verification and append-only collaboration resources. They must be reused unchanged.
* Existing `/api/v1/incidents` routes in `src/api/app.py` offered basic list/detail, lifecycle, assignment, empty timeline, evidence and preview endpoints. Filtering was offset-based and lacked environment scoping, cursor binding, safe evidence projection and a workbench response.
* The Console had only `/incidents/:incidentId`; its page was static. There was no incident inventory route.
* Approval policy already rejects missing, expired, cross-tenant and self-approved requests in `services/approvals`. The action catalogue is deny-by-default. No durable action executor is configured, and execution correctly fails rather than simulating success.

## Ownership and boundaries

Team 3 owns `services/incident_manager/`, `services/workflows/`, incident/workflow API modules, Console incident/automation features, focused incident/workflow tests, and these capability documents. This implementation uses those extension points.

Shared files that must not be generally changed include `src/api/app.py`, domain models, Console API facades, generated schemas/clients and shared shell/navigation. The only shared changes are additive router registration and the existing Console route table entry; no shared contract or domain model was changed. Team 0 directories, migrations, build configuration, release resources and product ledgers remain untouched.

## Implementation decision

The dedicated `/api/v1/incident-workbench` router coexists with legacy compatibility routes. It uses the authenticated tenant only, requires an explicit environment, and delegates to the injected production Elasticsearch repository. The workbench adds bounded filtering/sorting, query-bound cursors, typed safe projections, OCC revisions, append-only collaboration events, and honest preview-only automation states.
