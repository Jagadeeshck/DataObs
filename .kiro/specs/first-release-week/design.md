# Design — first release certification and product slices

## Architecture
Sources (OTLP / OpenLineage / Kafka / limited packaged providers) → DataObs API and workers → tenant/environment-scoped Elasticsearch indices and evidence → canonical Quality/Stream/Job/Lineage/Data Product projections → incident correlation and redaction-safe notification outcomes → React DataObs Console.

Kibana/Elastic remain core analysis/storage. API/Console/worker images and migrations packaged via Docker/Helm with external secured Elasticsearch in the supported certification profile. Never create parallel incident engines or separate product UIs.

## Release control plane
GitHub source commit + exact workflow producer runs → metadata/JUnit/evidence and artifact digests → independent verification → Gate 0 → frozen candidate → Teams 1–5 evidence → protected platform/security/supply-chain certification → release authority GO → immutable tag/digest artifact publication.

## Version conflict handling
The Oct 31 main bump declares DataObs v1.0.0, Elasticsearch/Kibana 9.5.5 and client 9.5.0, while older readiness documents remain v0.2.0/9.4.2 and NO_GO. Resolve by inspecting actual runtime, Helm, CI and release gate schema, then regenerate truth through canonical scripts; do not manually edit generated outputs or assume old passes prove the new matrix.

## Trust and data model
Every observation: tenant, environment, source, collection/evidence time, freshness, status, confidence/coverage where meaningful, correlation IDs, provenance. Keep zero separate from no data. Notification delivery records may be failed/unknown; never assume success.

## Failure handling
If ES unavailable: expose unavailable/error; no fake healthy data. If provider unknown: preserve unknown and checkpoint safety. If artifact incomplete: release NO_GO. If browser fixtures pass but live API fails: reject integrated acceptance.
