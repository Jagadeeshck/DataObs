# Connector and Schema projections

Kafka Observer writes one deterministic Connector document for tenant, environment, cluster and connector and one Schema subject document for tenant, environment, registry/cluster and subject. Connector health uses only measured state and failed-task count. Subject versions are newest-first and bounded to 100 (the collector maximum); definitions are discarded.

Connector and Schema persistence completes before their independent checkpoint advances. A write exception follows the normal failed-attempt path, retains the previous successful checkpoint, increments failure metadata, and emits only an exception category. Lease semantics are unchanged. Fixed read aliases, tenant/environment exact filters, exact IDs, request timeouts, source allowlists, deterministic ordering and bounded arrays form the query boundary.
