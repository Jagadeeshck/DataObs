# Current product baseline

## Pathway Intelligence backend v1

The backend supports fenced incremental OpenTelemetry Kafka evidence processing,
durable event watermarks and overlap replay, canonical node/edge projections,
bounded complete and partial pathway assembly, explainable health/latency and
bottleneck calculations, bounded comparison, impact classifications, canonical
Elasticsearch-backed APIs, and durable pathway SLO CRUD. Monitor evaluation,
payload inspection, automatic remediation, and major Console visualisation are
not part of this baseline.

## Lineage and job/run investigation

The console baseline includes tenant-scoped Jobs inventory, Job 360, Run 360, run comparison, and bounded dataset/column lineage exploration. Canonical lineage responses disclose evidence coverage, confidence, partial/missing states, and truncation rather than inferring unobserved relationships. Hosted Elasticsearch 9.4.2, browser, and accessibility evidence is owned by the `lineage-analysis-console` workflow artifact and is not promoted from local-only results.

> Audit date: 2026-07-27. Implementation baseline: local commit `5164762a6337a44a76ad2c7574a78edc048a70b3`, including merged PR history through #168. Final pull-request-head hosted run identifiers remain pending and no local result is presented as hosted evidence.

## Kafka Stream Observer backend v1

The backend composes bounded Kafka inventory, assigned consumer-group offsets, optional Kafka Connect, and optional Schema Registry collection. Capability-aware scheduling, Elasticsearch leases/checkpoints, canonical top-level projections, and explainable lag/retention intelligence are implemented. The `stream-observer-backend-v1-evidence` hosted artifact is defined but remains pending for the final commit; therefore this baseline does not claim real-stack certification.

## 1. Product identity

DataObs is a proprietary, Elasticsearch-native Data Observability and Data Streams Monitoring product owned by KJC InfoTech Limited. Elasticsearch and Kibana are authoritative; OpenTelemetry and OpenLineage are ingestion standards. The standalone DataObs Console is the operational UI. The canonical six-pillar model remains the target, not a claim that every pillar is implemented.

## 2. Target Elastic Stack

Certification definitions pin Elasticsearch and Kibana **9.4.2**. Compatibility with other versions is not certified by this baseline.

## 3. Storage migrations

The released forward migration registry spans `0001_product_foundation` through `0021_lineage_analysis_explorer`. Existing migrations remain immutable. The registry checksum ledger and the comparison against the branch base are mandatory gates.

Focused hosted certification is defined by `data-quality-monitoring`, `job-run-backend`, and `lineage-analysis-console`. Their exact-commit artifacts must pass a separate download-and-verification job; until a successful final-head run exists, the related capabilities remain functional but unvalidated.

## 4. Implemented API domains

The checked-in OpenAPI contract exposes health and migration status; assets, quality results/checks/runs and lineage; tenants and collection/scanner control; monitors, baselines, recommendations and coverage; Data Products, memberships, proposals, dependencies, impact and revisions; findings, incidents, approvals and actions; job/run exploration; pathways and topology; and Kafka/stream, consumer-group, connector and schema views. Presence in OpenAPI is not proof of authorization, browser usability, or hosted execution.

## 5. Implemented Console routes

Implemented routes are `/`, `/flow`, `/assets`, `/assets/:assetId`, `/pathways`, `/pathways/:pathwayId`, `/incidents/:incidentId`, `/streams`, `/data-products`, `/data-products/:productId`, plus stream cluster, topic, consumer-group, connector, and schema detail routes. Final-head browser and accessibility evidence remains a blocker.

## 6. Workers and services

Runnable Dockerfiles exist for the API, Console, quality worker, scanner worker, monitor runtime, pathway worker, and Kafka observer. Collection Manager has an implemented service library but no dedicated production Dockerfile/entrypoint, so release packaging must not invent its image.

## 7. Collection mechanisms

Implemented foundations include OpenTelemetry OTLP, OpenLineage ingestion, Elastic Agent/Fleet/EDOT adapters, PostgreSQL scanner, Kafka observer, and DataObs scanner/collection coordination. Demo-specific collectors and fixtures do not expand supported production coverage.

## 8. End-to-end certification contracts

CI defines Elasticsearch 9.4.2 Data Product foundation and reconciliation profiles and a quality-to-incident signal path covering persistence, OTel correlation, finding/incident creation, deduplication, tenant isolation, Slack/PagerDuty/ServiceNow outcomes, partial failure, redaction, and API retrieval. These remain `functional_unvalidated` until successful final-head hosted artifacts are retained and independently verified.

## 9. CI evidence inventory

Defined retained artifacts include `incident-migration-occ-artifacts`, Python test and migration-plan artifacts, `e2e-signal-path`, PostgreSQL, Kafka/OpenLineage and unified-certification artifacts, Console/browser artifacts, image SBOM/security artifacts, `data-product-foundation`, and Data Product reconciliation evidence. The final PR must record exact run URL, job conclusions, artifact IDs/names, hashes where defined, and independent verification result. At this baseline those final-head identifiers are **pending**, never inferred.

## 10. Deployment and package coverage

The release inventory is limited to components with Dockerfiles and supported entrypoints: API, Console, quality worker, scanner worker, monitor runtime, pathway worker, and Kafka observer. The Helm foundation currently deploys only API, quality worker, and OpenTelemetry Collector; it is not production-ready. Images must be pinned by semantic version, Git SHA, or digest. Grafana Alloy and other sample applications are excluded from the production inventory.

## 11. Security posture

Services and repositories contain tenant-scoping, strict Elasticsearch mappings, OCC/idempotency controls, redaction tests, dependency auditing, image scanning, and SBOM gates. OIDC/RBAC and comprehensive production tenant enforcement, HA, backup/restore, and a release rehearsal remain incomplete. Evidence bundles must exclude tokens, webhooks, authorization headers, and raw sensitive payloads.

## 12. Known blockers

- No successful retained hosted evidence is available for the final PR head in this checkout.
- Browser/accessibility, scale, HA, backup/restore, rolling-upgrade, and production security evidence is incomplete.
- Issue #25 may be closed as completed only after the final-head `e2e-signal-path` artifact passes.
- Release publication must remain gated on exact-commit CI and certification results.
- Helm coverage is partial and is not a supported production installation.

## 13. Explicitly unsupported

FinOps, Business Observability, AI/Agent Observability, autonomous remediation, new cloud and messaging providers, and full beta deployment hardening are not delivered by this baseline. POC/demo/sample assets are not supported production runtime.

## 14. Next milestone

The recommended next focused branch is `codex/oidc-rbac-tenant-enforcement`, followed only by core Data Quality Monitoring, Job/Run Explorer, Data Streams Monitoring, Incident and Automation Workbench, and full beta deployment hardening as evidence gates allow.

## Stream 360 Core Console v1

The supported core browser scope is Streams Inventory, Topic 360, and Consumer Group 360. These views consume measured projection fields, preserve zero versus missing evidence, provide URL-backed server filters and accessible table alternatives, and expose no actions. Cluster, Connector, Schema, and Pathway Console redesigns remain deferred. Exact-commit hosted evidence is defined by `stream-360-core-console.yml`; completion remains contingent on its successful final-head run.

## Kafka Cluster 360 Console v1

The dedicated cluster route provides typed, bounded and tenant-isolated cluster overview, broker, topic, consumer-group, connector and operational-health views. Unknown and measured zero are distinct; Changes and Incidents honestly remain `not_configured` without providers. Optional 30-second polling pauses when hidden. Exact-commit hosted certification is defined by `cluster-360-console.yml` and remains pending until its artifact is retained and independently verified.

## Parallel delivery foundation

The repository defines six ownership workstreams and a planned Beta 1 sequence. These governance and validation foundations do not promote Beta 1 or add product behavior; certification remains evidence-led through the shared contract in `docs/development/certification-evidence-contract.md`.

## Beta deployment packaging v1

Team Platform owns the implemented Beta 1 Kubernetes package for API, Console, Quality Worker, Scanner Worker, Monitor Runtime, Pathway Worker, Kafka Observer, optional bundled OpenTelemetry Collector, and the migration Job. Elasticsearch remains external. Collection Manager, Elasticsearch, Kibana, identity and Grafana Alloy are excluded. Certification is `functional_unvalidated` until final-head hosted smoke, upgrade/rollback, and independent evidence succeed.
