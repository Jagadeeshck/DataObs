# Multi-broker messaging observability

Collected native, Elastic, and OTel observations enter explicit adapters and canonical Stream 360 contracts. The registry is static and rejects unknown systems. Collection is asynchronous and outside API handlers. Kafka compatibility models remain intact.

SQS depth is approximate backlog, Pub/Sub backlog belongs to subscriptions, RabbitMQ ready/unacknowledged counts retain their names, Kinesis delay is iterator age, and Event Hubs lag exists only with checkpoint evidence. Service Bus has no Event Hubs partition semantics. Pulsar remains not implemented until authoritative production collection exists.

## Streaming schema intelligence

Kafka Schema Registry is the initial authoritative integration. Schema support for Kinesis, SQS, RabbitMQ, Pub/Sub, Event Hubs, and Service Bus is reported as unsupported/not configured unless instrumentation, a cloud registry, contract metadata, or reviewed declaration supplies authoritative evidence. Subject string similarity alone is never an authoritative cross-broker binding.
