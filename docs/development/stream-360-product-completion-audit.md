# Stream 360 product completion audit

Baseline: `4700e18` (merge of PR #100). Migrations `0001` through `0010` were inspected and are unchanged. No migration was added: the existing Kafka read aliases are sufficient for this increment, while action and SSE production persistence still require a demonstrated mapping and operational validation before a forward migration is justified.

> PR #100 introduced the Stream API and Console foundation. This completion gate replaces placeholder detail screens and empty comparison/action responses with measured, tenant-scoped product workflows validated against the real Kafka stack.

| Capability | PR #100 state | Blocking gap | Required correction | Test evidence |
|---|---|---|---|---|
| Inventory | Fixed-alias list with cursor | UI used a static example and had no request cancellation | Console now queries the tenant/environment API, preserves URL filters, cancels superseded requests, and renders honest states | Console typecheck/build; real-stack Playwright still required |
| Cursor | HMAC, expiry, tenant/environment/filter binding | No route/resource/sort binding or key rotation; result documents were mutated | Added canonical encoding validation, route/resource/sort fingerprints, previous-key verification, and separate sort metadata | `tests/stream_360/test_stream_pagination.py`, `test_product_completion.py` |
| Detail pages | One placeholder component | No measured requests or URL-addressable active tabs | Active tabs fetch only their explicit subresource, expose tab/tabpanel semantics, keyboard movement, loading and data-status evidence | Console typecheck/build; axe against real stack still required |
| Explicit API surface | Generic detail only | Required operational subresources absent | Added bounded, tenant-scoped route families for cluster, topic, group, connector, and schema evidence | OpenAPI generation and API integration validation required |
| Comparison | Empty deltas and zero samples | Configured evidence was represented as absent | Historical fixed-alias samples now produce absolute/valid percentage deltas and explicitly list missing evidence | `test_comparison_uses_measured_samples_and_reports_missing_evidence` |
| Connector actions | Always returned `awaiting_approval` | No allowlist, tenant isolation, idempotency conflict, history or event | Added a lifecycle boundary, allowlist, idempotency, action history, audit identity fields, and safe update events | `test_action_is_tenant_bound_idempotent_and_allowlisted`; durable external adapter remains required |
| Stream SSE | Absent | No replay, tenant filter, safe payload schema or event version | Added authenticated scoped SSE, bounded replay, `Last-Event-ID`, event allowlist and payload allowlist | `test_sse_payload_and_replay_are_tenant_isolated`; multi-process persistence/load validation remains required |
| Kibana links | Absent | SSRF and destination injection risk | Added an HTTPS-origin and destination allowlisted builder with encoded tenant/environment/resource state | `test_kibana_links_reject_ssrf_and_query_injection` |
| Inspection | Disabled | Scope was not explicit | Remains disabled by default and now checks inspection scope | API RBAC integration tests remain required |
| Real-stack evidence | Not provided | Three-broker Console, Playwright, axe and tenant denial unproven | Keep the pull request draft until the required environment and hosted gates pass | **Open blocker** |

## Honest completion status

This increment removes the explicit Console placeholder and empty comparison behavior, but it is **not production-ready**. The in-process action and SSE stores are adapter boundaries, not durable multi-replica storage. Real Kafka Compose, Elasticsearch 9.4.2 migration/alias validation, browser tenant denial, Playwright, axe, scale, Trivy, SBOM, and hosted workflow evidence remain blocking. No non-Kafka provider, destructive action, autonomous remediation, raw message inspection, connector secret, or schema body exposure was added.
