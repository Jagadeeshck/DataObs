# Cluster 360 Console preflight audit

## Dependency and migration

The branch starts at merge commit `66c4af6`, the merge of PR #182, **Build Stream Inventory and Core Stream 360 Console**. The terminal migration is `0021_lineage_analysis_explorer`; this work adds no migration and does not change migrations 0001–0021.

## Projection evidence inventory

| Projection | Stored/allowlisted evidence relevant to Cluster 360 |
|---|---|
| Cluster | `cluster_id`, `name`, `controller_id`, `broker_count`, `topic_count`, `consumer_group_count`, `health`, `reason_codes`, `observed_at`, `source_coverage` |
| Broker | `broker_id`, `cluster_id`, `host`, `port`, `rack`, `controller`, `health`, `reason_codes`, `observed_at`, `source_coverage` |
| Topic | `stream_id`, `topic`, `name`, `cluster_id`, partition/replication counts, health, rates, lag and retention-risk summaries, observation evidence |
| Partition | `topic_id`, `partition_id`, `leader_id`, `leader_available`, replicas/ISR, `under_replicated`, `offline_replicas`, health and observation evidence |
| Consumer group | `group_id` (also collected as `consumer_group_id`), cluster, state, protocol, coordinator, members/assignments and optional lag summaries |
| Connector | connector ID/name, cluster, type/classification, state and bounded task/worker/failure summary fields when the optional Connect provider supplies them |

The former generic subresource handler read `brokers`, `health`, `topics`, `consumer_groups`, `connectors`, `changes`, and `incidents` as nested cluster fields. The observer deliberately stores brokers, topics, partitions and groups in separate projections, so those generic reads were not evidence-backed.

## Coverage and limitations

Overview identity and observer summary counts are measured. Broker inventory, topic inventory, consumer-group inventory and partition replication state have current projection evidence. Connector evidence is partial/unknown unless Kafka Connect collection is configured. Changes and cluster-related incidents have no configured cluster provider in v1 and must report `not_configured`, not an evidence-free empty success. Partition-derived failure counts remain unknown when the partition projection is missing. Host and rack remain unknown when absent.

Naming inconsistencies retained at ingestion boundaries include `group_id` versus `consumer_group_id`, `stream_id`/`topic_id`/`topic`, `controller_id` versus broker `controller`, and singular `under_replicated`/`leader_available` versus cluster summary count names. The API normalizes only its typed response; it does not fabricate missing values.

Security review found the historic global safe list includes topic configuration for Topic 360. Cluster broker and connector queries therefore use narrower per-resource allowlists that exclude credentials, SASL/TLS/JMX authentication material, arbitrary broker configuration and connector connection details.
