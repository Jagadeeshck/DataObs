# Collection Capability Matrix

This matrix describes target collection paths, not certification. The provider-neutral Integration SDK v1 is
`functional_unvalidated`; it supports explicit registration and capability negotiation but does not make any listed
cloud provider implemented. Provider status is governed by the capability ledger and exact-commit evidence.

| Source | Existing Elastic integration | EDOT/OTel | DataObs connector required | Collected capabilities | Credential model | Minimum privileges | Output datasets |
|---|---|---|---|---|---|---|---|
| Linux | Yes system | Yes host receivers | No | host metrics/logs/process/filesystem | Fleet secret refs | agent host read | Elastic system datasets |
| Windows | Yes system/windows | Yes host receivers | No | host metrics/logs/events | Fleet secret refs | agent host read | Elastic system datasets |
| Kubernetes | Yes kubernetes | Yes k8s receivers | No | pods/nodes/events/logs/traces | service account | read cluster resources | kubernetes, otlp |
| Docker | Yes container/docker logs | Yes | No | container metrics/logs | socket scoped | docker read | container datasets |
| AWS | Yes aws | Yes | Yes for v2 data platform evidence | RDS/Aurora, Glue, Athena, EMR Serverless, S3, Lambda, SageMaker, MWAA, Redshift and Redshift Serverless bounded metadata and allowlisted metrics | AWS chain/web identity/optional AssumeRole | least-read IAM | dataobs provider evidence |
| Azure | Yes azure | Yes | Sometimes | metrics/logs/data factories | managed identity/Key Vault | reader | azure, dataobs cloud |
| GCP | Yes gcp | Yes | Sometimes | metrics/logs/data services | workload identity/Secret Manager | viewer | gcp, dataobs cloud |
| PostgreSQL | Yes postgresql | Yes | Yes | ops metrics plus schema/freshness/profile | secret ref | connect/catalog/select opt-in | dataobs database streams |
| MySQL | Yes mysql | Yes | Yes | ops metrics plus schema/freshness/profile | secret ref | information_schema/select opt-in | dataobs database streams |
| Microsoft SQL Server | Yes mssql | Yes | Yes | ops metrics plus schema/freshness/profile | secret ref | view definition/select opt-in | dataobs database streams |
| Oracle | Yes oracle | Yes | Yes | ops metrics plus schema/freshness/profile | secret ref | dictionary/select opt-in | dataobs database streams |
| Snowflake | Partial | Yes | Yes | warehouse/query/schema/profile | key pair/secret ref | monitor/select opt-in | dataobs warehouse streams |
| Redshift | Yes aws/redshift | Yes | Yes | cluster/query/schema/profile | IAM/secret ref | system table/select opt-in | dataobs warehouse streams |
| BigQuery | Yes gcp | Yes | Yes | jobs/schema/profile | service account | metadata viewer/data viewer opt-in | dataobs warehouse streams |
| Databricks | Partial | Yes | Yes | jobs/lakehouse/schema/lineage | PAT/OIDC secret ref | read metadata/jobs | dataobs lakehouse streams |
| Trino/Presto | No generic | Yes | Yes | catalog/schema/query/profile | secret ref | information_schema/select opt-in | dataobs sql streams |
| Athena | Yes aws | Yes | Yes | queries/schema/profile | IAM | Glue/Athena read | dataobs query streams |
| MongoDB | Yes mongodb | Yes | Yes | ops metrics plus collection metadata | secret ref | clusterMonitor/read opt-in | dataobs documentdb streams |
| Cassandra | Yes cassandra | Yes | Yes | ops metrics plus schema | secret ref | system_schema read | dataobs nosql streams |
| Elasticsearch | Yes elasticsearch | Yes | Sometimes | cluster/index/data stream health | API key | monitor/read opt-in | elasticsearch, dataobs index |
| OpenSearch | Custom/generic | Yes | Sometimes | cluster/index health | API key | monitor/read opt-in | dataobs opensearch |
| Kafka | Yes kafka | Yes messaging spans | Sometimes | broker/topic/consumer lag/lineage | SASL/secret ref | describe/read metrics | kafka, dataobs stream |
| Kinesis | Yes aws | Yes | Sometimes | stream metrics/events | IAM | read metrics/describe | aws.kinesis, dataobs stream |
| SQS | Yes aws | Yes | No | queue metrics/message spans | IAM | sqs read attrs | aws.sqs, otlp |
| RabbitMQ | Yes rabbitmq | Yes | No | broker/queue metrics | secret ref | monitoring user | rabbitmq |
| Pub/Sub | Yes gcp | Yes | Sometimes | topic/sub metrics/lineage | workload identity | viewer | gcp.pubsub, dataobs stream |
| Airflow | No/generic API | Yes | Yes | DAG runs/tasks/lineage | API secret ref | read DAG/runs | dataobs jobs |
| dbt | No/generic | Yes | Yes | manifests/run results/tests | token/files | read artifacts/API | dataobs dbt |
| Spark | Yes where platform exists | Yes | Yes | jobs/stages/lineage | platform secret | event/log read | dataobs spark |
| Glue | Yes aws | Yes | Yes | jobs/crawlers/lineage | IAM | glue read | aws.glue, dataobs jobs |
| Lambda | Yes aws/lambda | Yes instrumentation | No | invocations/cold start/events | IAM/layer env | lambda exec/monitor | aws.lambda, otlp |
| Azure Data Factory | Yes azure | Yes | Yes | pipelines/runs/lineage | managed identity | reader | azure.adf, dataobs jobs |
| Synapse | Yes azure | Yes | Yes | jobs/sql/schema | managed identity | reader/select opt-in | dataobs synapse |
| Dataflow | Yes gcp | Yes | Yes | jobs/metrics/lineage | workload identity | viewer | dataobs dataflow |
| Cloud Composer | Yes gcp | Yes | Yes | Airflow managed runs | workload identity | composer viewer | dataobs jobs |
| Tableau | Generic REST | No | Yes | workbooks/datasources/lineage | token secret | metadata API read | dataobs bi |
| Power BI | Generic REST | No | Yes | datasets/reports/refresh | Entra app secret | tenant read | dataobs bi |
| Looker | Generic REST | No | Yes | explores/dashboards/lineage | API secret | metadata read | dataobs bi |
| generic REST API | Custom HTTP/CEL | Yes if instrumented | Sometimes | API metrics/payload metadata | secret ref | endpoint read | custom/api/dataobs |
| generic SQL/JDBC source | SQL input | Yes | Yes for stateful scan | custom query plus scan/profile | secret ref | metadata/select opt-in | dataobs sql |
| generic files/object storage | Elastic file/cloud inputs | Yes | Yes for profiling | file inventory/freshness/schema | IAM/secret ref | list/read opt-in | dataobs file |
