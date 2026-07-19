# Job/run integration compatibility

Validated 2026-07-19 against published, stable documentation; pins are compatibility targets, not a production-readiness claim. Event fixtures remain the contract gate because package version compatibility alone is insufficient.

| Component | Tested version | Supported range | Integration package | Reason | CI coverage |
|---|---:|---:|---|---|---|
| Elasticsearch | 9.4.2 | project target | official Python client | system of record | required (pending real stack) |
| Kibana | 9.4.2 | project target | saved objects/APIs | investigation | required (pending real stack) |
| OpenLineage spec/client | 1.39.0 | 1.x stable event schemas | `openlineage-python==1.39.0` | portable event contract and unknown-facet preservation | fixture contract |
| Airflow | 3.1.7 | provider-declared `>=2.11.0` | `apache-airflow==3.1.7` | pinned stable orchestration target | required (pending integration) |
| Airflow OpenLineage provider | 2.11.1 | Airflow `>=2.11.0` | `apache-airflow-providers-openlineage==2.11.1` | official listener/extractors | required (pending integration) |
| dbt Core | 1.10.15 | artifact schemas explicitly parsed by version | `dbt-core==1.10.15` | Core artifacts work without Cloud | unit fixtures; real invocation pending |
| Apache Spark | 3.5.7 | 3.5.x target | OpenLineage listener + event logs | replayable operational evidence | parser unit; real listener pending |
| Python | 3.11 | repository-supported 3.11 | runtime | matches project type-check target | blocking quality |
| Java/Scala | Java 17 / Scala 2.12 | Spark 3.5 distribution matrix | integration runtime | Spark listener ABI compatibility | pending container |

References: [Airflow provider requirements](https://airflow.apache.org/docs/apache-airflow-providers-openlineage/stable/index.html), [Spark 3.5.7 monitoring/event logs](https://spark.apache.org/docs/3.5.7/monitoring.html), [OpenLineage integrations](https://openlineage.io/integrations/), and [dbt artifacts](https://docs.getdbt.com/reference/artifacts/dbt-artifacts). CI/demo images must use exact tags and constraints—never `latest`. Unknown facets are stored in a bounded Elasticsearch `flattened` field.
