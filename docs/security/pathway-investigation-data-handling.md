# Pathway investigation data handling

Investigation APIs fail closed without trusted request tenant, environment, and principal state. Request bodies cannot supply tenant, environment, actor, index, query, or relation allowlists. Repositories use fixed aliases/source fields, tenant/environment/resource filters, 5-second timeouts, 90-day ranges, result caps, deterministic sorting, and signed context-bound cursors.

Snapshots contain metadata identifiers and evidence references, not payload values. Cache and authorization state are not shared across tenant/environment boundaries. Team 1 never queries Team 2/3 private indices and never writes incident or remediation state.
