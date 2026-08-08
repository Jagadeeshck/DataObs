# Azure Data Platform Collector v1

The provider is a tenant-scoped Integration SDK v1 provider for Azure Public Cloud. It accesses only explicitly configured subscription resources: ADF factories, Synapse workspaces, and ADLS Gen2 accounts. It never crawls management groups, Resource Graph, resource groups, or a whole subscription.

ADF and Synapse pipeline definitions and operational runs are provider-native source evidence. Team 2 may consume only canonical IDs, names, types, statuses, timestamps, durations, counts, retry numbers, and stable failure categories. Parameters and values, expressions, activity input/output, SQL, notebook paths/output, linked-service details, user identities, raw errors, and lineage are excluded. Team 4 does not write canonical job, run, task, stage, or lineage stores.

Families are isolated per configured resource and collector. A denied activity history does not remove pipeline-run evidence; a pool or prefix failure does not remove sibling inventory. Collection Manager persists evidence before advancing its OCC-protected generic checkpoint. Stable canonical IDs deduplicate overlap replay. The handoff uses generic provider observations and collection-run evidence from migration 0022; no Azure mapping is required.

History requests contain explicit after/before bounds, overlap, ordering, page and row ceilings. Logical checkpoint families are documented in `integrations/azure/evidence.py`; runtime checkpoint identity additionally includes trusted tenant, environment (trusted context attributes/persistence routing), integration, provider, subscription/resource identity, evidence family and capability. The current generic runtime advances only after the provider iteration and persistence completes; family failures are retained as partial failures.

ADLS prefix scans are disabled by default and aggregate count, bytes, and min/max modification times without path names. `adls_prefix_max_last_modified` describes storage-object modification freshness only—not upstream pipeline freshness, business-data freshness, or data quality. Truncated scans emit partial state and no complete counts.
