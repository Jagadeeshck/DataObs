# Kafka Cluster 360 Console v1

The read-only `/streams/clusters/:clusterId` route requires `streams:read` and provides Overview, Brokers, Topics, Consumer Groups, Connectors, Health, Changes and Incidents. Topic, group, connector and incident identifiers link to their existing detail routes. Connector 360 and Schema 360 redesign remain deferred.

## Evidence and health

All related-resource queries use the exact tenant, environment and cluster ID, fixed aliases, safe source allowlists, deterministic search-after pagination, a maximum page size and a request timeout. Broker and connector configuration, credentials, connection URLs, SASL material, TLS private-key locations and JMX authentication are never returned.

Health is calculated from bounded current broker, topic, partition, consumer-group and connector projections. A measured leaderless partition is critical; offline replicas and failed connectors are critical; under-replication is degraded. A measured broker set without a controller is degraded. Missing partition evidence produces `unknown`, not healthy and not zero. A measured zero is displayed as zero. Observations older than five minutes reduce confidence and add `stale_observations`. Reason codes explain evidence, not root cause.

`complete`, `partial`, `stale`, `unknown`, `not_configured`, and `unavailable` describe evidence availability, not Kafka guarantees. Coverage identifies providers; confidence falls for missing projection classes and stale observations. Missing inputs are displayed explicitly.

## Refresh and states

Refresh is manual by default. Users may enable 30-second **polling**; it pauses while the document is hidden and is not described as real-time streaming. Changing tenant/environment cancels obsolete requests and reloads evidence. Topic filters and the selected tab are URL-backed; filter changes clear the pagination cursor.

Changes and incidents return `Not configured` until a cluster-scoped provider exists. This is not proof that no changes or incidents occurred. Missing host/rack, lag, offsets, metrics and counts remain Unknown. No write, restart, inspection or remediation controls are present.

## Known limitations

The health query reads at most 200 resources of each projection class and is an operational bounded view, not an unbounded cluster census. Connect evidence depends on optional collection. There is no raw configuration or message inspection, and correlation labels never assert causation. Hosted Elasticsearch, Playwright and axe claims require the retained exact-commit workflow artifact.
