# Team ownership

Ownership is review accountability, not permission to bypass shared contracts. `@Jagadeeshck` is the interim GitHub owner until dedicated teams exist.

| Team | Mission | Owned directories | Tests | Workflows and docs |
|---|---|---|---|---|
| **Team 0 — Platform, Security and Release** | Secure platform, storage and releases. | `packages/elastic_store/`, `src/security/`, `src/config/`, `deploy/`, `helm/`, `docker/`, `.github/workflows/`, `scripts/certification/`, `docs/release/` | Migration, security, release and certification tests | Owns shared CI, release and security docs |
| **Team 1 — Streams and Pathways** | Stream and pathway observation. | `services/kafka_observer/`, `services/pathway_worker/`, `services/product_query/stream_*`, `packages/pathways/`, `integrations/kafka/`, `integrations/kafka_connect/`, `integrations/schema_registry/`, `src/api/stream_routes.py`, `src/api/pathway_routes.py`, Console `features/streams/` and `features/pathways/`, `tests/stream_360/` | Stream/pathway tests | Capability workflows and docs |
| **Team 2 — Data Quality, Jobs and Lineage** | Quality, runtime and lineage. | `services/monitoring/`, `services/monitor_runtime/`, `src/data_observability/`, monitor/job/run/lineage route modules, `integrations/airflow/`, `integrations/dbt/`, `integrations/spark/`, Console jobs/lineage/quality features, `tests/monitoring/`, `tests/job_run/` | Quality/job/lineage tests | Capability workflows and docs |
| **Team 3 — Incidents and Automation** | Incident response and safe automation. | `services/incident_manager/`, `services/workflows/`, incident/workflow domain models and API modules, Console incidents/automation features, `tests/incidents/`, `tests/workflows/` | Incident/workflow tests | Capability workflows and docs |
| **Team 4 — Integrations and Collection** | Provider collection and SDKs. | `integrations/` except Team 1 Kafka and Team 2 Airflow/dbt/Spark, `services/collection_manager/`, `services/scanner_worker/`, `services/scanner/`, `packages/collectors/`, `config/integrations/`, `tests/integrations/` | Integration/collector tests | Integration workflows and docs |
| **Team 5 — Console and Product Experience** | Coherent navigation, state and experience. | Console `app/`, `layouts/`, `components/`, `state/`, `auth/`, and command-center/flow-map/integrations/onboarding features | Shared Console component/state tests | Console shell workflows and UX docs |

## Rules for every team

Allowed changes are within owned capability surfaces, their focused tests, and capability documentation. Shared directories (`src/api/`, `packages/domain_model/`, `ui/dataobs-console/src/api/`, generated schemas, fixtures, root configuration, and product ledger) require the relevant owner plus Team 0 approval. Teams must not modify another team's surface, redefine shared contracts, alter released migrations, weaken security/tenant isolation, or claim certification without hosted evidence. Test owners maintain focused suites; workflow owners maintain only their capability caller while Team 0 owns reusable workflows. Documentation owners keep runbooks and capability evidence truthful.
