# Team 4 RabbitMQ messaging collector v1

The `rabbitmq` v1 Integration SDK provider uses only RabbitMQ's Management HTTP API. It performs bounded GET polling of overview, health, vhosts, vhost-scoped queues, exchanges, and bindings. Collection emits generic provider observations containing the existing Team 1 RabbitMQ observation envelope; Team 1 remains responsible for canonical messaging semantics and projections.

Queue depth gauges preserve measured zero and mark absent inputs missing. Provider cumulative counters and recent provider rates remain distinct and are not interpreted as processing success, unique failures, or offset lag. Raw arguments and routing keys are discarded; a SHA-256 binding fingerprint retains deterministic identity. A queue is classified as a DLQ only when its declared dead-letter exchange and an observed exchange-to-queue binding prove that topology.

Connections, channels, consumer sessions, messages, AMQP, mutations, and Prometheus scraping are out of scope. A future **RabbitMQ Prometheus Metrics Collector v2** may add scalable historical metrics without changing Team 1 contracts.
