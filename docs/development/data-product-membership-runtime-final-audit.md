# Data Product membership and dependency runtime final audit

> PR #122 corrected cursor mechanics only. It did not complete the production membership and dependency runtime, and the strict mapping defect prevents the PR #121 writers from operating on real Elasticsearch until migration `0016` is applied.

Release readiness remains **blocked**. Hosted evidence is deliberately recorded as unavailable until a real hosted run produces a URL and retained artifacts; local or mocked results are not hosted certification.

| Capability | Current `main` state | Blocking defect | Implementation | Real evidence | Hosted evidence |
|---|---|---|---|---|---|
| 0016 mapping migration | Absent | Strict 0015 resources reject writer fields | Forward-only resource-specific updates in 0016 | Contract test; real ES pending | Pending |
| membership mapping | Incomplete shared mapping | Audit, exclusion, timestamps absent | Dedicated complete mapping | Serializer contract; ES pending | Pending |
| proposal mapping | Incomplete shared mapping | expiry, creation and missing inputs absent | Dedicated complete mapping | Serializer contract; ES pending | Pending |
| decision mapping | Incomplete shared mapping | event/outcome/OCC fields absent | Dedicated immutable-event mapping | Serializer contract; ES pending | Pending |
| dependency mapping | Incomplete shared mapping | graph, removal and revision fields absent | Dedicated projection/tombstone mapping | Serializer contract; ES pending | Pending |
| impact mapping | Incomplete shared mapping | serialized summary fields absent | Mapping limited to model fields | Serializer contract; ES pending | Pending |
| writer/mapping contract | Absent | No complete field comparison | Model-to-mapping regression contract | Unit test; ES pending | Pending |
| resource-specific sorts | Implemented by #122 | Requires mapped sort verification | 0016 maps all auxiliary sort fields | Real pagination pending | Pending |
| product cursor | Implemented | Hosted verification absent | Signed scoped cursor | Unit evidence only | Pending |
| revision cursor | Implemented by #122 | Real ES verification absent | Full search-after tuple | Real ES pending | Pending |
| membership cursor | Implemented by #122 | Real ES verification absent | updated_at/id/_id sort | Real ES pending | Pending |
| proposal cursor | Implemented by #122 | Real ES verification absent | created/revision/id/_id sort | Real ES pending | Pending |
| decision cursor | Implemented by #122 | Real ES verification absent | decided/id/_id sort | Real ES pending | Pending |
| dependency cursor | Implemented by #122 | Real ES verification absent | removed/upstream/version/_id sort | Real ES pending | Pending |
| manual membership | Partial | Full event-first ES proof absent | Membership service | Real ES pending | Pending |
| manual membership replay | Partial | Crash/replay proof absent | Hashed scoped idempotency | Real ES pending | Pending |
| proposal generation | Partial | Evidence adapters and certification incomplete | Bounded service path | Real ES pending | Pending |
| proposal revisioning | Partial | Immutable revision proof absent | Revision identity model | Real ES pending | Pending |
| accept / reject / expire / supersede | Partial | Full OCC race certification absent | Repository mutation methods | Real ES pending | Pending |
| exclude | Partial | Event-first race proof absent | Service-mediated exclusion | Real ES pending | Pending |
| pending/applied decision outcomes | Model incomplete | Strict mapping rejected outcomes | Expanded immutable decision contract | Contract test; ES pending | Pending |
| decision reconciliation | Partial | Crash matrix incomplete | Reconciliation service | Real ES pending | Pending |
| dependency replace | Partial | End-to-end OCC proof absent | Dependency service/repository | Real ES pending | Pending |
| dependency removal evidence | Model incomplete | Tombstone timestamps/revision absent | `removed_at` and `removed_by_revision` | Contract test; ES pending | Pending |
| dependency OCC | Partial | Concurrent certification absent | Product revision and graph version | Real ES pending | Pending |
| direct upstream / direct downstream | Partial | API/browser proof absent | Deterministic bounded traversal | Unit evidence only | Pending |
| transitive upstream / transitive downstream | Partial | Real graph proof absent | Deterministic bounded traversal | Unit evidence only | Pending |
| cycle path | Model incomplete | Path was not returned | Explicit bounded `cycle_path` | Unit pending | Pending |
| truncation | Implemented | Browser/real-stack proof absent | Explicit graph flag | Unit evidence only | Pending |
| impact | Partial | Consumer/status contract incomplete | Metadata-only typed summary | Contract test; ES pending | Pending |
| read APIs | Partial | Real-stack certification absent | Typed routes | API tests pending | Pending |
| mutation APIs | Partial | Complete action matrix absent | Service-delegating routes | API tests pending | Pending |
| OpenAPI / generated client | Stale for incomplete runtime | Drift generation required | Pending after routes stabilize | Pending | Pending |
| Members actions | Evidence-oriented | Full actions absent | Pending | Playwright pending | Pending |
| Lineage route/actions | Missing/incomplete | PR #121 thread unresolved | Pending real traversal route | Pending | Pending |
| Dependencies editor | Incomplete | Full mutation UX absent | Pending | Playwright pending | Pending |
| Revisions pagination / next-page behavior | Cursor fixed, UX incomplete | Append/focus/dedup proof absent | Pending | Playwright pending | Pending |
| Elasticsearch 9.4.2 | Not certified | Service unavailable locally/hosted | Dedicated job required | Pending | Pending |
| Playwright / axe / security | Not certified | Production-stack journeys absent | Dedicated gates required | Pending | Pending |
| hosted CI | Not run | No run URL or manifest | Dedicated jobs required | N/A | Pending |
| PR #121 threads | Five unresolved | Evidence threshold not met | Do not resolve prematurely | Pending | Pending |
| PR #118 thread | P1 unresolved | Immutable replay hosted proof absent | Do not resolve prematurely | Pending | Pending |

## Scope and next milestone

Migration 0016 is additive and does not modify migrations 0001–0015. It adds only fields serialized by the membership, proposal, decision, dependency, and impact models. Elasticsearch rejects incompatible pre-existing field types while applying these updates, and strict indices continue rejecting unknown fields.

No capability is promoted on the strength of this audit. Data Product SLOs, reliability, and coverage remain the explicit next milestone, after this gate has real-stack, browser, accessibility, security, and hosted evidence.
