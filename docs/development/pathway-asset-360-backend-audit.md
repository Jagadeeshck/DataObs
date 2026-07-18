# Pathway Explorer and Asset 360 backend audit

Baseline: merged commit `eb2077238070508ea990e839a863295cecdf3ebb` (PR #88 merge commit). The repository clone did not contain a configured Git remote, so this audit uses the merge commit and its first parent rather than the PR description.

| Concern | Current implementation | Gap | Required correction | Test evidence |
|---|---|---|---|---|
| Real Elasticsearch-backed API reads | Console queries read stable `-read` aliases through `ElasticsearchConsoleRepository`. | Asset sections and pathway investigation were absent. | Add bounded repository queries; never expose Elasticsearch clients or arbitrary documents to the browser. | Repository and API tests; demo stack remains required. |
| Tenant and environment isolation | Every Console search builds mandatory isolation filters; entity reads validate both fields. | New graph and asset routes need the same boundary. | Apply isolation before traversal and reject cross-scope entity IDs. | Unit coverage exists; two-tenant container proof remains required. |
| Lineage confidence and evidence | Flow topology contains projection evidence but has no unified typed edge contract. | Structural and inferred relationships could be confused with observed lineage. | Require evidence type, confidence, observation time, source reference, integration, coverage and active state on every edge. | Contract and path-search tests. |
| Path calculation correctness | Flow Map only displays a topology projection. | No bounded alternative path search, cycle handling or explanation. | Use deterministic loopless breadth-first enumeration bounded by 12 hops, 20 returned paths and a hard work cap; rank with returned factors. | `tests/test_path_search.py`. |
| Asset health derivation | No Asset 360 health response. | Missing signals could be rendered as healthy/zero. | Return reasons, confidence and missing inputs; use `unknown`/`not_configured`. | Contract validation; integration proof remains required. |
| Saved-view behaviour | Saved views persist tenant and owner fields. | Existing list filtering uses a wildcard environment and field validation is incomplete. | Validate route-specific fields and enforce tenant/owner scope before use. | Existing saved-view tests; hardening remains a known limitation. |
| SSE behaviour | Endpoint emits scoped keepalive with replay ID. | Durable replay and targeted invalidation are not implemented. | Filter by tenant/environment and invalidate only keys named by supported event types. | Existing API tests; reconnect integration proof remains required. |
| Browser/API contract generation | OpenAPI TypeScript generation is present. | Drift was not a blocking proof in PR #88. | Generate from committed OpenAPI and fail CI on diff. | `pnpm api:generate`, typecheck. |
| Playwright execution | Command Center/Flow Map scenarios exist. | PR #88 did not prove a real browser against Elasticsearch in its execution environment. | Run against the container demo without fixture interception. | Not claimed until container run succeeds. |
| Accessibility execution | Semantic shell and an axe scenario exist. | New graph/table alternatives require checks. | Provide semantic tables, route list alternatives, focus visibility and reduced motion. | Automated browser axe proof remains required. |
| Container-backed validation | Console demo compose exists. | No successful execution evidence was available in PR #88. | Extend a real Elasticsearch 9.4.2 demo and preserve failure artifacts. | Not claimed in this audit. |

This audit does not claim DataObs is production-ready.
