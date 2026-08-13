# Team 1 multi-broker Team 4 handoff

No Team 4 collection code is changed. Team 1 consumes bounded observation envelopes from the existing provider framework. Live certification remains owned by Team 4.

| Provider | Required evidence | Source API | Minimum permission | Collection owner | Normalization owner | Checkpoint owner | Tests |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AWS Kinesis/SQS | Team 4 v1 provider-native inventory, configuration, operational metrics, DLQ relations | CloudWatch and metadata/list APIs; never GetRecords or ReceiveMessage | read-only list/describe/metrics | Team 4 | Team 1 | existing worker runtime | fixture normalization/runtime |
| RabbitMQ | cluster/vhost/exchange/queue/binding counters | management monitoring API; never consume/basic.get | monitoring read-only | Team 4 | Team 1 | existing worker runtime | fixture normalization/runtime |
| Google Pub/Sub | topic/subscription metadata and monitoring metrics | Cloud Monitoring/admin list/get; never pull/acknowledge | viewer/monitoring read | Team 4 | Team 1 | existing worker runtime | fixture normalization/runtime |
| Azure messaging | namespace/entity metadata and Azure Monitor metrics | ARM/Azure Monitor; never receive/peek | Reader/Monitoring Reader | Team 4 | Team 1 | existing worker runtime | fixture normalization/runtime |
| Pulsar | no authoritative collector | none | none | Team 4 | Team 1 contract only | none | truthful not-implemented status |

Team 4 now emits adapter-compatible resource envelopes and native metric evidence. The current Team 1 runtime persists only resource families; metric/backlog/retention/DLQ projection remains a Team 1 handoff gap.
