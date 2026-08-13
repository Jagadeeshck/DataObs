# Operating the Team 4 RabbitMQ collector

Start from `config/integrations/rabbitmq-messaging.example.yaml`, provision the monitoring-only account, install its password reference, and validate HTTPS trust. Runs are scheduled or on demand through Collection Manager; there is no RabbitMQ-specific scheduler.

Scopes are `rabbitmq/cluster/health`, `rabbitmq/vhosts`, and `rabbitmq/vhost/<fingerprint>/{queues,exchanges,bindings}`. The generic Collection Manager persists observations before advancing its OCC checkpoint. A failed vhost or endpoint family emits a stable partial failure without invalidating successful siblings. Pagination, observations, response bytes, request time, and total time are bounded.

Optional statistics can be absent while inventory remains healthy. Treat `partial` and `missing_inputs` as coverage statements, not zeros. Investigate `authentication_failed`, `access_denied`, TLS errors, timeouts, response limits, and pagination limits without capturing raw bodies or credentials.
