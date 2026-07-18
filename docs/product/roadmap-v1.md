# DataObs Roadmap v1

Phase 0 preserves open product epics as roadmap scope rather than pretending they are complete.

| Issue | Requirement destination | Pillar | Milestone | Collection mechanism | Storage model | API/UI destination | Security/licensing notes |
|---|---|---|---|---|---|---|---|
| #46 | AI agents, autonomous remediation, guarded workflow execution | Automated incident response | v1.3 | Elastic Workflows plus DataObs Advisor | workflow events data streams, policy state indices | Advisor and remediation console | human approval, audit, least privilege |
| #47 | Azure observability across platform and data services | Platform and pipeline observability | v1.1 | Elastic Azure integration, EDOT, DataObs connectors | azure/otlp/dataobs streams | cloud integration pages | managed identity, Azure licensing |
| #48 | GCP observability across platform and data services | Platform and pipeline observability | v1.1 | Elastic GCP integration, EDOT, DataObs connectors | gcp/otlp/dataobs streams | cloud integration pages | workload identity, API quotas |
| #49 | Snowflake observability | Data quality, pipeline, cost | v1.1 | DataObs Snowflake connector plus OTel | dataobs warehouse streams and state | warehouse asset pages | key pair auth, warehouse cost limits |
| #50 | Multi-cloud OpenLineage correlation | Lineage and impact | v1.1 | OpenLineage events from Spark, dbt, Airflow, Glue, ADF, Dataflow | lineage event streams + graph state | lineage API/topology | tenant isolation and source auth |
| #51 | DataObs Advisor recommendations | Advisor/remediation | v1.2 | Elastic ML, rules, curated heuristics, optional AI | recommendation streams + mutable cases | Advisor UI and workflows | audit, explainability, model licensing |
