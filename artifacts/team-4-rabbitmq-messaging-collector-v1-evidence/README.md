# team-4-rabbitmq-messaging-collector-v1-evidence

Team = Team 4. Branch `codex/team-4-rabbitmq-messaging-collector-v1`; PR title **Team 4: add RabbitMQ messaging collector v1**. Base SHA `ad31a9a38d69dd98b2191318b331a7134f5339e4`; exact implementation SHA is recorded by the commit containing this artifact.

Status: `functional_unvalidated`. Provider `rabbitmq` version `1`; target RabbitMQ 4.3.x (4.3.4 fixture identity); HTTP dependency is Python standard library. Unit evidence covers verified TLS/hostname configuration, Basic secret references, health, vhosts, queues, exchanges, bindings, queue types, DLQ proof, backlog/counters/redelivery, missing versus zero, routing-key/argument redaction, Team 1 envelope compatibility, partial failures, GET-only behavior, and absence of message retrieval, AMQP consume/publish/ack, and mutation methods.

Migration required: false. Terminal graph leaf: `0033_team1_stream_schema_intelligence_runtime`; graph valid. Live RabbitMQ, permission degradation, persistence/replay integration, and exact-head hosted evidence were not executed and remain gates. The implementation does not claim certification or production readiness.
