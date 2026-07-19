# Kafka Observer real-stack gate

The compose fixture provides Elasticsearch 9.4.2, three KRaft brokers, Connect, Schema Registry, two PostgreSQL databases, OTel Collector and the DataObs runtime boundaries. Run the seed script and runner from the repository root. PLAINTEXT and fixed database passwords are local-only fixtures.

The fixture creates metadata only. It does not inspect or persist Kafka record values. Broker outage, connector failure and rebalance scenarios require the integration test driver; deterministic partition-health fixtures are used where container runtimes cannot safely manipulate broker storage. Stream APIs and Console 360 pages remain the next gate.
