# DataObs Feature Matrix

| Feature | Phase 0 status | Target pillar | Milestone | Collection mechanism | Elasticsearch storage model | API/UI destination | Evidence/non-goal |
|---|---|---|---|---|---|---|---|
| Elastic Agent/Fleet reuse | defined | all ingest pillars | v1.0 | Elastic Agent/Fleet | Elastic data streams | Kibana/Fleet and integration APIs | collection-plane architecture |
| EDOT/OpenTelemetry layer | defined | all pillars | v1.0 | EDOT/OTel Collector | traces, metrics, logs data streams | investigation APIs/Kibana | integration stack validates OTLP path |
| DataObs Scanner SDK | foundational implementation | Data Observability | v1.0 | Scanner worker/connectors | scanner state and quality/profile streams | scanner APIs/future Console | redaction, close, timeout, checkpoint tests |
| Distribution drift (#24) | partial unless full criteria pass | Data Observability | v1.0/v1.1 | quality worker/scanner profiling | quality and baseline indices | quality API/Kibana | missing criteria remain roadmap scope |
| End-to-end alert path (#25) | implemented in CI definition | Data Observability + Incident Response | v1.0 | API, OTel Collector, Elasticsearch, mock webhooks | `dataobs-traces`, quality indices | quality APIs/alert adapters | real containers required before closing |
| AWS Lambda OTel (#28) | partial/supersession candidate pending re-query | Pipeline and Job Observability | v1.1 | Lambda OTel layer/EDOT | AWS/OTLP streams | serverless integration pages | no new expansion in Phase 0 |
| dbt (#29) | partial/supersession candidate pending re-query | Pipeline and Job Observability | v1.1 | artifacts parser/dbt Cloud polling | dbt run/test streams | pipeline APIs/UI | no new expansion in Phase 0 |
| Anomaly detection (#30) | partial/supersession candidate pending re-query | Data Observability | v1.1 | quality worker/Elastic ML | anomaly streams/baselines | anomaly APIs/UI | deterministic proof required |
| Alloy multi-tenancy (#31) | superseded optional integration unless fully validated | Optional Integrations | optional v1.x | Grafana Alloy exporter | optional external backend | optional docs/API | Alloy is not core architecture |
| Grafana Terraform (#32) | superseded optional integration unless fully validated | Optional Integrations | optional v1.x | Terraform provider | optional dashboard state | optional Grafana dashboards | Kibana and future Console are primary |
| AI agents (#46) | superseded by roadmap | Incident Response/Remediation | v1.3 | Elastic Workflows/DataObs Advisor | workflow/audit indices | Advisor/remediation UI | not completed in Phase 0 |
| Azure (#47) | superseded by roadmap | Pipeline/Job Observability | v1.1 | Elastic Azure/EDOT/connectors | azure data streams | cloud integration UI | not completed in Phase 0 |
| GCP (#48) | superseded by roadmap | Pipeline/Job Observability | v1.1 | Elastic GCP/EDOT/connectors | gcp data streams | cloud integration UI | not completed in Phase 0 |
| Snowflake (#49) | superseded by roadmap | Data Observability | v1.1 | future Snowflake connector | warehouse streams/state | warehouse UI | not completed in Phase 0 |
| Multi-cloud OpenLineage (#50) | superseded by roadmap; ingestion foundation exists but cross-cloud scope unproven | Lineage/Impact | v1.1 | OpenLineage across orchestrators/clouds | lineage graph/event streams | topology/impact UI | not completed in Phase 0 |
| DataObs Advisor (#51) | superseded by roadmap | Incident Response/Remediation | v1.2 | ML/rules/optional AI | recommendations/cases | Advisor UI | not completed in Phase 0 |

## Product foundation update

The product foundation now tracks six canonical pillars: Platform Observability, Data Pipeline and Job Observability, Data Observability, FinOps and Cost Observability, Business Observability, and AI and Agent Observability. Elasticsearch/Kibana is the mandatory primary product platform; OpenSearch, Grafana Cloud, AMP, AMG, Alloy, and other exporters are optional integrations only.
