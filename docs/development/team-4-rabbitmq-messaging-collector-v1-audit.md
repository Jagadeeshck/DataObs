# Team 4 RabbitMQ messaging collector v1 audit

1. **Team:** Team 4 — Integrations and Collection.
2. **Audited base SHA:** `ad31a9a38d69dd98b2191318b331a7134f5339e4`.
3. **Dynamic terminal migration:** helper failed with a pre-existing `NameError`; graph reports `0033_team1_stream_schema_intelligence_runtime`.
4. **Migration graph:** valid, one leaf, 33 migrations.
5. **Migration doctor:** no standalone doctor exists; graph/release checks are used and the helper defect is recorded.
6. **Existing RabbitMQ collection:** none; only Team 1 contracts/adapter, capability documentation, and Elastic references existed.
7. **Team 1 contract:** provider/system `rabbitmq`; namespace, exchange, queue, dead-letter queue; safe `RabbitMqFacet`.
8. **Envelope:** trusted tenant/environment plus safe scope, kind/id/name, observation quality, method/integration/schema metadata.
9. **Capability state:** collector becomes `functional_unvalidated`; certification and production readiness remain blocked.
10. **HTTP dependency:** Python standard-library `urllib`; no optional dependency or import failure added.
11. **Versions:** primary target RabbitMQ 4.3.x; 4.3.4 fixture identity; no live broker test was available. Online verification was attempted but the search service returned HTTP 401.
12. **Authentication:** Basic with username plus `env:`/`file-ref:` password reference only.
13. **TLS:** production HTTPS, certificate and hostname verification; file-referenced CA; localhost HTTP only for disposable tests.
14. **Pagination:** mandatory `pagination=true`, default 100, hard page size 500, bounded pages/results/responses.
15. **Queue metrics:** depth gauges, cumulative counters, and provider rates remain distinct; absent is not zero.
16. **Binding privacy:** raw key/arguments dropped; deterministic SHA-256 fingerprint retained.
17. **DLQ mapping:** DLX retained structurally; DLQ queue only when an observed binding proves it.
18. **Checkpoint:** generic Collection Manager OCC/persist-before-advance behavior; logical scopes documented.
19. **Migration:** not required; no index or released migration changed.
20. **Limitations:** Management API current evidence only; no AMQP/messages, identities, detailed nodes, Prometheus, live/hosted certification, or production-ready claim.
