# DataObs Feature Matrix

| Feature | Phase 0 status | Target pillar | Milestone | Evidence |
|---|---|---|---|---|
| Elastic Agent reuse | defined | Platform observability | v1 | collection-plane architecture |
| EDOT/OpenTelemetry layer | defined | All pillars | v1 | collection-plane architecture |
| DataObs Scanner SDK | foundational implementation | Data quality/catalog | v1 | `packages/agent_sdk`, `services/scanner_worker` |
| PostgreSQL metadata connector | reference implementation | Data quality/catalog | v1 | `integrations/databases/postgres` |
| Distribution drift | pre-existing, verified in closure report | Data quality | v1 | quality tests |
| End-to-end alert path | pre-existing with skipped container tests | Incident response | v1 | integration tests documented |
| AWS Lambda OTel | pre-existing partial/completed criteria documented | Platform/pipeline | v1 | lambda integration docs/tests |
| AI agents/remediation | superseded roadmap | Advisor/remediation | v1.2-v1.3 | roadmap issue #46 |
| Azure observability | superseded roadmap | Platform/pipeline | v1.1 | roadmap issue #47 |
| GCP observability | superseded roadmap | Platform/pipeline | v1.1 | roadmap issue #48 |
| Snowflake observability | superseded roadmap | Warehouse observability | v1.1 | roadmap issue #49 |
| Multi-cloud OpenLineage | superseded until cross-cloud criteria are tested | Lineage | v1.1 | roadmap issue #50 |
| DataObs Advisor | superseded roadmap | Advisor | v1.2 | roadmap issue #51 |
