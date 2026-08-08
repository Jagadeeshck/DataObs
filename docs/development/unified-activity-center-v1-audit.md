# Unified Activity Center v1 contract audit

**Audited base:** `e99ff14c74f0df4e65818dadd539d17ae96b0317` (local checkout; no Git remote was configured). **Terminal migration derived by script:** `0028_pathway_investigation_history`.

The audit inspected merged changes #231–#236 and the Console route, shell, context, API, dashboard/watchlist, search, investigation and observability contracts. Open-PR inspection was unavailable because this checkout has no configured GitHub remote or `gh` integration.

| Activity source | Owner | API | Timestamp | Cursor | Severity/actionability | Bounded | v1 |
|---|---|---|---|---|---|---|---|
| Incident Workbench | Team 3 | `GET /api/v1/incident-workbench` | `last_observed_at`, `opened_at` | opaque | backend severity/state; explicit policy | limit 25, 7d | Included |
| Quality findings | Team 2 | quality findings | evaluation timestamp is not present in list summary | opaque | backend finding severity | uncertain | Excluded: no auditable feed timestamp |
| Job/run reliability | Team 1 | entity detail APIs | detail-only | none | backend state | no bounded transition list | Excluded |
| Stream intelligence | Team 1 | detector/forecast detail APIs | mixed observation/forecast | opaque by endpoint | backend | no common transition summary | Excluded |
| Pathway history | Team 1 | pathway-scoped history | recorded timestamp | opaque | backend | entity-scoped | Excluded: requires inventory fan-out |
| Lineage/schema impact | Team 2 | asset-scoped changes/impact | change timestamp | endpoint-specific | backend impact | entity-scoped | Excluded: requires inventory fan-out |
| Integrations | Team 4 | integration inventory | current state | none | backend state | inventory | Excluded: no bounded transition feed |
| Safe Remediation | Team 3 | incident-scoped action APIs | operation timestamps | opaque | backend approval/execution state | incident-scoped | Excluded: would require incident N+1 |
| Elastic Workflows | Team 3 | incident integration summaries | execution timestamps | bounded integration contract | backend status | incident-scoped | Excluded: no cross-incident safe summary |
| Elastic Cases | Team 3 | incident integration summaries | case timestamps | bounded integration contract | backend case state | incident-scoped | Excluded: no cross-incident safe summary |
| Platform lifecycle | Team 0 | environment/fleet APIs | operation timestamp | endpoint-specific | authoritative state | scoped | Excluded pending Team 0 activity-read review |

The v1 registry therefore activates one honest provider rather than downloading inventories or performing N+1 requests. Workflow inputs/outputs, arbitrary Elasticsearch queries, direct Elasticsearch access, cross-tenant reads and unbounded history are prohibited.
