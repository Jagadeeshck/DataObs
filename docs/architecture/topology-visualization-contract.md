# Topology visualization contract

The shared Cytoscape renderer accepts provider-neutral dataset, table, file, job, run, stream, queue, subscription, producer, consumer, integration, incident, monitor, and data-product nodes. Kafka, Kinesis, SQS, RabbitMQ, Google Pub/Sub, Azure Event Hubs, Azure Service Bus, and Pulsar remain provider facets. Backlog, consumer lag, message age, queue depth, and delivery delay retain distinct labels.

The backend supplies traversal, direction, depth, cycles, confidence, snapshot time, and blast-radius membership. The browser only renders it. Limits are 100 nodes/200 edges; a capped result must set `truncated`, visibly disclaim incomplete coverage, and expose the same relationships in a keyboard-operable table.
