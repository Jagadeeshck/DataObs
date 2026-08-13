# Messaging console data handling

The Console calls authenticated DataObs APIs only—never brokers or Elasticsearch. It never reads payloads or handles passwords, cloud keys, tokens, connection strings, account/project identifiers, or credentials. URLs preserve existing safe canonical routes and exclude tenant/environment values as path identity.

Telemetry is low cardinality and allowlisted to provider type, resource-kind category, capability state, chart type, count/duration buckets, and interaction category. Resource names/IDs, topic/queue/subscription names, tenants, environments, endpoints, namespaces, and raw metrics are discarded.
