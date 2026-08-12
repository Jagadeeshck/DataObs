# Team 1 stream-to-Data-Product impact v1 audit

Audited from `main` SHA `28ae56851b6d88cc87573e97cebc2a981dc6c266` on 2026-08-12. The local clone has no
configured remote, so fetch/pull could not be repeated; the checkout already contains merge commits for PR #245
(`ec73806`) and PR #232 (`80f6935`). The executable registry reports terminal migration
`0030_team1_multi_broker_messaging_runtime`. Migration doctor was invoked but Elasticsearch was not running locally
(`ConnectionRefusedError`), so no migration was added: v1 resolves bounded evidence on read.

| Requirement | Existing source | Owner | Gap | Decision |
| --- | --- | --- | --- | --- |
| Multi-broker projection | `services/stream_observer/multi_broker_runtime.py` | Team 1 | Team 2 vocabulary is Kafka-centric | Canonical Team 1 adapter; no Team 2 model mutation |
| Pathway topology/history | `services/pathway_worker/topology_builder.py`, `history_projector.py` | Team 1 | No product binding history | Return `history_unavailable` until evidence is collected |
| Blast radius | `src/api/pathway_routes.py` | Team 1 | No optional product branch | Public resolver is ready; route shaping remains follow-up |
| Reliability runtime | `services/monitor_runtime` | Team 1 | Stream state adapter required | Accept explicit degradation evidence only |
| Stream Intelligence | `packages/pathways/intelligence.py` | Team 1 | No product semantics | Keep semantics in pure product-impact package |
| Data Product model | `packages/domain_model/data_product.py` | Team 2 | Non-Kafka broker output vocabulary absent | Preserve strong `kafka_topic`; document Team 2 handoff |
| Data Product repository | `services/data_products/repository.py` | Team 2 | Large private persistence surface | Narrow read port; never expose/write ES details |
| Product impact | `services/data_products/impact.py` | Team 2 | `lineage` and `pathways` always missing | Team 1 public evidence adapter; Team 2 integration deferred |
| Dependency traversal | `services/data_products/dependencies.py`, `dependency_service.py` | Team 2 | Team 1 needs downstream context | Delegate via bounded public port, do not clone graph |
| Product SLO reads | `services/data_products/slo.py`, `reliability.py` | Team 2 | Resource correlation required | Only related failed SLO upgrades exposure state |
| Lineage APIs | `services/lineage_intelligence/impact.py` | Team 2 | Availability may be partial | Consume public evidence and preserve missing status |
| Incident/intake | `services/incident_*`, `services/rca` | Team 3 | Optional product counts absent | Document read-only handoff; never set severity/root cause |
| Investigation provider | `packages/pathways/investigation.py`, `src/api/pathway_routes.py` | Team 5/1 | Product provenance not mapped | Backend-shaped evidence is future route integration |
| Stream/Pathway UI | `ui/dataobs-console/src/features/streams/Stream360.tsx`, `features/pathways/PathwayExplorer.tsx` | Team 1/5 | Product cards/overlays absent | Defer perceptible UI until backend API route is integrated |
| Storage/migrations | `packages/elastic_store/registry.py` | Team 0 | No current query-performance evidence | No projection and no migration in v1 |

## Decision record

The delivered slice establishes pure contracts, state/score/confidence semantics, canonical multi-broker identity, hard
bounds, scope defense, failure isolation, and a Team 2 read boundary. It intentionally does not claim historical,
projection, API, UI, real-stack, scale, or hosted certification completion. Those limitations remain explicit rather
than representing missing evidence as healthy.
