# Team 5 Beta 1 Console integration preflight audit

Audit date: 2026-08-01. Audited local base: `232a8e0`. The checkout did not
contain a remote; an `origin` remote was added, but the private repository could
not be fetched because credentials and the GitHub CLI are unavailable. The
local merged history after PR #191 was therefore inspected through PRs #192,
#193, #194, #195, #196, and #197. Open Console pull requests and hosted Actions
runs could not be queried and remain an explicit evidence gap.

Before implementation, the audit read the ownership, delivery, Console
architecture/state, product baseline/ledger, evidence contract, and Beta 1
manifest documents; inspected the application router, typed registry, layouts,
state, authentication, API clients, every feature route, browser suites, and
Console workflows; and ran the three mandatory repository preflight checks.

## Findings before implementation

| Area                    | Finding                                                                                                                                                                                                        | Closure required                                                                                                                 |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Duplicate routes        | `/quality`, `/quality/monitors/:monitorId` were rendered both explicitly and below `quality/*`.                                                                                                                | Remove the wildcard implementation and render only manifest entries.                                                             |
| Missing registry routes | Dynamic routes, auth routes, monitor inventory/authoring, run comparison, and all stream detail routes existed only as child strings or router declarations.                                                   | Give every routable implementation a unique manifest entry.                                                                      |
| Ownership               | Data Quality was incorrectly attributed to Team 4.                                                                                                                                                             | Attribute Quality routes to Team 2.                                                                                              |
| Availability            | Incident Inbox and Detail existed while the parent was marked `not_configured`. Static implementation and tenant configuration were collapsed.                                                                 | Mark implementation truthfully and resolve tenant capability state separately.                                                   |
| Permissions             | Only Incidents and Integrations declared permissions; deep links inherited no explicit policy and the router did not apply UX permission handling.                                                             | Put permission metadata on every protected manifest entry and guard rendered protected routes without weakening API enforcement. |
| Deep links              | Features construct several entity URLs locally and the registry's dynamic matcher does not escape literals or safely decode identifiers.                                                                       | Add a canonical, encoding entity-link resolver and tested route matching.                                                        |
| Bundles                 | Only Streams, Data Products, and the duplicated Quality wildcard were lazy. All other major capability pages were eager.                                                                                       | Move major route implementations behind loader mappings while retaining the shell/auth bootstrap.                                |
| Boundaries              | A React Router `errorElement` was supplied to declarative `<Route>`, where it is ineffective, and raw import/runtime error messages could be shown.                                                            | Add an actual shared React error boundary with safe retry/recovery.                                                              |
| Loading                 | One global fallback always announced “Loading Stream evidence…”.                                                                                                                                               | Use the matched route's suspense label.                                                                                          |
| Metadata                | Breadcrumbs showed only a parent label, dynamic IDs had no hierarchy, and document titles were not centrally managed.                                                                                          | Generate breadcrumbs and titles from route metadata with safe fallback labels.                                                   |
| Navigation              | Static availability controlled links; trusted runtime capability state was used only for a count banner.                                                                                                       | Resolve implementation, permission, and tenant configuration independently.                                                      |
| Browser coverage        | Existing mocked coverage exercised the shell, Flow, Integrations, Onboarding, and not-found only. It did not cover the full Beta cross-capability journey, unauthorised/unavailable states, or route recovery. | Add deterministic manifest coverage and expand browser certification without production fixture fallback.                        |
| Accessibility           | Axe coverage omitted most capability routes; there was no shared dynamic breadcrumb/title assertion.                                                                                                           | Add shared-route axe/keyboard coverage and preserve capability-owned tests.                                                      |
| Workflow/evidence       | The caller emitted two differently named artifacts, lacked independent verification, route/bundle/browser reports, and the required exact-commit name.                                                         | Produce `console-beta-integration-v1-evidence` and verify it using repository provenance conventions.                            |
| API contracts           | `/api/v1/auth/me` supplies trusted permissions/capabilities, but capability status has no separate status endpoint contract. An absent capability value must remain unknown rather than healthy.               | Treat absent/unreachable runtime status as unavailable/unknown and never infer it from bundle loading.                           |
| Build drift             | Merged Quality auxiliary files import compatibility functions/types no longer exported by `src/api/quality.ts`; the audited `tsc -b` fails in those Team 2 files.                                                | Team 2 must reconcile its API adapter; Team 5 must not invent or replace capability contracts.                                   |
| Cross-team conflicts    | Merge-resolution commits manually accumulated route declarations and caused the Quality overlap. No capability-owned business logic needs replacement.                                                         | Limit capability changes to loader registration and shared navigation integration.                                               |

## Preflight results

- `python scripts/check_team_boundaries.py`: passed (10 deterministic fixture contracts; no migration added).
- `python scripts/check_generated_artifacts.py`: passed.
- `python scripts/check_docs_links.py`: passed.

## Certification posture

No hosted run URL, artifact ID, or independently verified final-head evidence is
available in this environment. Local results must not promote the Console above
`functional_unvalidated`. Workflow dispatch is the mechanism for producing
exact-commit proof after the branch is pushed.
