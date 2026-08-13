# Team 5 platform fleet console v1 contract audit

Audited base: `96d6e4fc0e20d11ee7dcaca5f681660d5dd2be52` (PR #261 is ancestor; merged changes through #262 were inspected). The route policy, domain models, service transitions, planning model, generated schema and Console navigation were read at this SHA. There is no configured Git remote, so open-PR inspection and pulling `main` were unavailable in this checkout.

## Endpoint contract

| Endpoint | Method | Permission | Read/Write | OCC | Idempotency | Preview | Safe Team 5 use |
|---|---|---|---|---|---|---|---|
| `/environments` | POST | `environments:write` | Write | No | Header | No | Excluded |
| `/environments` | GET | `environments:read` | Read | N/A | N/A | N/A | Inventory |
| `/environments/{id}` | GET | `environments:read` | Read | N/A | N/A | N/A | Detail |
| `/environments/{id}/transition` | POST | `environments:write` | Write | If-Match | Header | No | Excluded |
| `/clusters/register` | POST | `clusters:register` | Write | No | Header | No | Excluded |
| `/clusters` | GET | `clusters:read` | Read | N/A | N/A | N/A | Inventory |
| `/clusters/{id}` | GET | `clusters:read` | Read | N/A | N/A | N/A | Detail |
| `/installations` | POST | `installations:manage` | Write | No | Header | No | Excluded |
| `/installations` | GET | `installations:read` | Read | N/A | N/A | N/A | Inventory |
| `/installations/{id}` | GET | `installations:read` | Read | N/A | N/A | N/A | Detail |
| `/tenants` | POST | `tenants:provision` | Write | No | Header | No | Excluded |
| `/tenants` | GET | `tenants:provision` | Read | N/A | N/A | N/A | Inventory |
| `/tenants/{id}` | GET | `tenants:provision` | Read | N/A | N/A | N/A | Detail |
| `/tenants/{id}/{action}` | POST | provision/suspend/offboard by action | Write | If-Match | Header except approval defect | No | Excluded |
| `/tenants/{id}/offboarding-preview` | GET | `tenants:provision` | Read | N/A | N/A | Yes | Explicit user preview |
| `/fleet` | GET | `platform_operations:read` | Read | N/A | N/A | N/A | Overview |
| `/drift` | GET | `platform_operations:read` | Read | N/A | N/A | N/A | Evidence |
| `/capacity` | GET | `platform_operations:read` | Read | N/A | N/A | N/A | Truthful state/reference |
| `/deployment-plans` | POST | `installations:manage` | Metadata write | No | No | Calculated plan | Excluded: missing v1 safeguards |
| `/deployment-plans/{id}/transition` | POST | `installations:manage` | Metadata write | No | No | No | Excluded |
| `/promotions` | POST | `platform_promotions:execute` | Validation write | No | No | Validation | Excluded |

All paths are under `/api/v1/platform`. Route-policy permissions are authoritative; the router itself uses authenticated dependencies and central policy enforcement.

## Lifecycle matrix

| Resource | States | Allowed transitions | Read UI | Mutation UI v1 |
|---|---|---|---|---|
| Environment | requested, provisioning, configured, validating, ready, degraded, maintenance, upgrade_pending, upgrading, rollback_pending, retiring, retired, failed | Exact `ENV_TRANSITIONS` graph in Team 0 service | Yes | None |
| Cluster | discovered, registered, validating, ready, degraded, draining, unregistered | Exact `CLUSTER_TRANSITIONS` graph | Yes | None |
| Installation | planned, installing, migrating, validating, active, upgrading, rolling_back, degraded, suspended, removing, removed | No route transition contract | Yes | None |
| Tenant | requested, approved, provisioning, validating, active, suspended, offboarding, retention_hold, deleting, deleted, failed | Exact `TENANT_TRANSITIONS` graph | Yes | Preview only |
| Deployment plan | created, validated, approval_required, approved, executing, verifying, completed, failed, rollback_required, rolled_back | `DeploymentPlan.advance` graph; metadata only | No list/read API | None |
| Promotion | validated response | Gate validation only; not deployment | No read API | None |

## Baseline and boundaries

Terminal migration was `0031_team3_post_incident_review_analytics`. The capacity response is explicitly `unvalidated`. Lifecycle is never presented as health. The current list endpoints have no pagination; the UI does not derive fleet counts from joining them and labels unavailable fleet totals honestly. Release-readiness and bounded lifecycle activity APIs do not exist. No mutation endpoint is exposed.

## Reproduced baseline failures

| File | Exact error | Owner | Team 5 safe fix? | Blocks milestone? |
|---|---|---|---|---|
| `src/features/quality/QualityConsole.tsx` | `QualityOverviewView` is not exported | Quality capability owner (Team 2) | No, unrelated | Production build only |
| `src/features/quality/QualityFindings.tsx` | `qualityFindings` is not exported; dependent result types become unknown | Quality capability owner (Team 2) | No, unrelated | Production build only |
| `src/features/quality/QualityAuxiliary.tsx` and components | generated `Coverage`/`EvidenceEnvelope` contract mismatch | Quality capability owner (Team 2) | No, unrelated | Production build only |
| `src/investigation/providers.ts` | unsafe properties on `DataProduct | Asset` union | Investigation owner (Team 5, separate workstream) | Not in this focused PR | Production build only |
| Playwright runtime | Chromium executable is not installed | Environment | No code fix | Screenshot/Playwright only |

`pnpm typecheck`, lint, formatting, all 98 unit tests and visualization contracts pass. `pnpm build` uniquely uses project-build semantics and reproduces the unrelated errors above; bundle/performance checks cannot run without build output. The Vite dependency scan reproduces the two missing Quality exports. These were not modified to avoid crossing capability boundaries.
