# Operational dashboards v1 contract audit

Audited base: `70f77d85b17776fe2222d591788f145269479057`. The local checkout has no configured Git remote, so GitHub open-PR inspection and pulling `main` were not executable. The merge history after #227 contains #228 (Azure collector), #229 (platform lifecycle foundation), and #230 (safe-remediation closure). Earlier merged equivalents include Global Search (#222), Lineage Impact (#223), Stream Intelligence runtime (#225), and Investigation Workspace (#227). Terminal migration is derived by `scripts/release/current_terminal_migration.py`, never embedded in dashboard code.

The audit covered the authoritative route registry, product context, abort/visibility hooks, API modules, Command Center, flow map, search, investigation, Evidence components, Elastic Charts, Cytoscape, observability attribute policy, local/session storage, permissions and capability availability. Dashboard v1 activates only the bounded Command Center aggregate; other audited widgets remain permission-aware link-only surfaces until a bounded aggregate adapter is certified.

| Widget candidate                                    | Capability owner | API                          | Permission                 | Time-aware | Bounded             | Dashboard v1                                     |
| --------------------------------------------------- | ---------------- | ---------------------------- | -------------------------- | ---------- | ------------------- | ------------------------------------------------ |
| Estate health / pillars / work / coverage / changes | Team 5           | `GET /api/v1/command-center` | `assets:read`              | Yes        | Yes, 50 queue items | Active                                           |
| Assets / products                                   | Team 2           | `/assets`, `/data-products`  | `assets:read`              | Partial    | Paginated           | Excluded: entity lists are not aggregate widgets |
| Quality monitors/findings                           | Team 2           | quality API module           | `quality:read`             | Yes        | Paginated           | Link-only: aggregate mapping unclear             |
| Jobs / runs / reliability                           | Team 3           | jobs and reliability modules | `jobs:read`                | Yes        | Paginated           | Link-only: no shared summary adapter             |
| Lineage / changes / impact                          | Team 2           | lineage module               | `lineage:read`             | Yes        | Entity-scoped       | Link-only: requires entity input                 |
| Streams / reliability                               | Team 1           | streams/reliability modules  | `streams:read`             | Yes        | Paginated           | Link-only: no cross-stream aggregate contract    |
| Anomalies / forecasts / failure candidates          | Team 1           | stream intelligence module   | `streams:read`             | Yes        | Cursor bounded      | Link-only: resource-scoped semantics             |
| Pathways                                            | Team 1           | pathways module              | `lineage:read`             | Yes        | Paginated           | Link-only: no aggregate contract                 |
| Incidents / Event Storms                            | Team 4           | incident runtime modules     | `incidents:read`           | Yes        | Cursor bounded      | Link-only: avoid semantic remapping              |
| Integrations / collection                           | Team 5           | integrations APIs            | `integrations:read`        | Partial    | Paginated           | Link-only: configured is not healthy             |
| Platform operations / lifecycle                     | Team 0           | `/api/v1/platform/{section}` | `platform_operations:read` | No         | Section bounded     | Excluded: no Team 0 dashboard adapter review     |
| Watchlist                                           | Team 5           | No detail calls              | `console:read`             | No         | 25 entries          | Registered, session-only                         |

No new capability calculations, persistence API, migration, graph library, or analytics/query language is introduced.
