# Stream 360 API and Console audit

Baseline: `7553245` (merge of PR #99). Migrations 0001–0010 were reviewed and are unchanged; this slice adds no migration.

Kafka Observer supplies measured Kafka evidence. Stream 360 product-query services convert that evidence into tenant-scoped operational views. The Console must preserve measurement method, confidence, source coverage and missing-data state.

| Capability | Current evidence | Blocking gap | Required implementation | Test evidence |
|---|---|---|---|---|
| Read aliases and transforms | Observer aliases exist for Kafka projections | No consolidated Stream search projection | Retain fixed aliases; prove whether a grouped transform is necessary before adding migration 0011 | Repository source/tenant tests required |
| Product-query pattern | `ElasticsearchConsoleRepository` uses fixed aliases | Existing asset cursor exposes sort state | Stream repository adds fixed aliases, source allowlist and deterministic sort | Cursor unit tests |
| Tenant/environment isolation | Shared `isolation_filters` supplies both predicates | Route-family negative coverage incomplete | Require context on every query and cursor | Cross-tenant browser/integration test pending |
| Pagination | Assets use `search_after` | No public integrity boundary | HMAC cursor binds tenant, environment and filter fingerprint | Tamper, mismatch and expiry unit tests |
| API/OpenAPI | FastAPI app and checked-in OpenAPI exist | Full route inventory/client snapshot is incomplete | Typed router and regenerated client | OpenAPI drift pending |
| Console routes/navigation | React Router shell and shared Pathway/Flow screens exist | Six Stream routes were absent | Lazy Stream inventory and five 360 details; retain shared topology contracts | Typecheck/build required |
| Shared states/evidence | Existing pages preserve data status | Full component library is incomplete | Extract reusable states as UX matures | axe pending |
| SSE | Generic authenticated keepalive endpoint exists | Stream event replay/cache contract absent | Add bounded tenant-scoped event store and targeted client invalidation | Real-stack SSE test pending |
| Monitor/recommendation/incident/RCA/workflow | Domain services and workflow pack exist | Stream joins and browser review incomplete | Query by stable resource identity without declaring hypotheses confirmed | Integration tests pending |
| Kibana links | No complete Stream-specific allowlist helper found | URL injection boundary absent | Add configured base URL and destination allowlist | SSRF/link tests pending |
| Playwright/axe | Playwright dependency exists | No complete real-stack browser evidence | Add all-route and default-denial scenarios | Pending |
| PR #99 real stack | Audit and merge commit provide collector artifacts | Hosted workflow evidence for PR head was not available in this checkout | Run three-broker product stack in CI | Pending |

## Gate decision

This work must remain draft. The collector/model artifacts are not treated as completed product screens. Real Elasticsearch 9.4.2, Kafka, approval, Playwright, axe, leakage, and hosted CI evidence remain release blockers; DataObs is not production-ready.
