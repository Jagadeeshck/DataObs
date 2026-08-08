# Multi-broker messaging observability v1 audit

Audited local `main` SHA: `e99ff14c74f0df4e65818dadd539d17ae96b0317`. This checkout has no configured remote, so `fetch`, hosted PR #232 metadata, and live provider validation were unavailable. The locally merged PR #232 commit `80f6935` and its investigation changes were inspected. Merge-marker validation passed. The dynamically determined terminal migration is `0028_pathway_investigation_history`.

Migrations 0009/0010 and 0023–0026 were inspected through the executable manifest. Existing strict Kafka projections cannot truthfully store all neutral resource/facet relations. This increment nevertheless adds no migration: it establishes the public normalized contract and adapters while collection and durable projection wiring remain unconfigured. Editing released migrations is prohibited; a later forward migration must follow terminal migration 0028 after Team 4 observation contracts are accepted.

| Provider | Inventory | Throughput | Backlog/Lag | Consumers | Retention | DLQ | Topology | OTel correlation | Collection source | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kafka | functional | functional | functional offset lag | functional groups | functional | partial | functional | partial | Kafka observer, Elastic, OTel | functional |
| Kinesis | partial | partial | partial iterator age | partial EFO/OTel | partial | unsupported | partial | partial | AWS/CloudWatch or Elastic AWS | partial |
| SQS | partial | partial | partial approximate backlog | unsupported groups | partial | partial | partial | partial | AWS/CloudWatch or Elastic AWS | partial |
| RabbitMQ | not_configured | not_configured | not_configured queue depth | not_configured | not_configured | not_configured | not_configured | partial | Elastic RabbitMQ/management API | not_configured |
| Google Pub/Sub | not_configured | not_configured | not_configured subscription backlog | partial OTel | not_configured | not_configured | partial | partial | GCP Monitoring/Elastic/OTel | not_configured |
| Azure Event Hubs | not_configured | not_configured | partial; lag needs checkpoints | not_configured | not_configured | unsupported | not_configured | partial | Azure Monitor/ARM/OTel | not_configured |
| Azure Service Bus | not_configured | not_configured | not_configured active messages | partial OTel | not_configured | not_configured | not_configured | partial | Azure Monitor/ARM/OTel | not_configured |
| Pulsar | not_implemented | not_implemented | not_implemented | not_implemented | not_implemented | not_implemented | not_implemented | not_configured | no authoritative repository collector | not_implemented |

Authoritative measurements are Kafka broker/admin offsets; CloudWatch Kinesis stream metrics and IteratorAgeMilliseconds; SQS approximate count and oldest-age metrics; RabbitMQ management queue/message stats; GCP Monitoring subscription metrics; and Azure Monitor entity metrics plus ARM metadata. OTel messaging spans are authoritative only for observed application identity and trace-correlated timing, not broker inventory or missing relationships. No adapter handles message content, credentials, policy documents, connection strings, SAS tokens, or arbitrary provider blobs.
