# Team 4 multi-broker collection handoff

| Provider | Required observation | Preferred source/API | Minimum permission and pagination | Rate/checkpoint | Redaction and normalized evidence |
| --- | --- | --- | --- | --- | --- |
| Kinesis | stream/shards, retention, CloudWatch throughput/iterator age | Describe/List APIs and CloudWatch | read/list; bounded NextToken | provider limits; per stream/window | no GetRecords; resource, shard, throughput, age |
| SQS | attributes, redrive summary, CloudWatch counts/age | GetQueueAttributes/ListQueues and CloudWatch | read/list; NextToken | bounded queue checkpoint | never ReceiveMessage; omit policy; queue/backlog/DLQ |
| RabbitMQ | vhost/exchange/binding/queue aggregates | Elastic or management read API | monitoring-only; page/page_size | bounded page checkpoint | omit arguments/credentials; routing and queue metrics |
| Pub/Sub | topic/subscription config and monitoring | Resource Manager/Monitoring | viewer/monitoring; pageToken | bounded resource checkpoint | never pull/ack; subscription backlog/DLQ |
| Azure messaging | ARM entity metadata and Azure Monitor metrics | ARM/Monitor | Reader/Monitoring Reader; nextLink | bounded metric window | no receive/peek/SAS; entity/throughput/backlog |
| Pulsar | inventory and broker aggregate metrics | authoritative source not selected | TBD read-only | TBD | no payload/config blob; keep runtime not_implemented |

All observations must carry tenant, environment, system/provider, account scope, location, kind and provider ID, observed/ingested times, status/confidence/coverage, collection source/method, and schema version.
