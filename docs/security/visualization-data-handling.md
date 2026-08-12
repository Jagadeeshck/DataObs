# Visualization data handling

Visualization telemetry is low-cardinality: visualization type, capability ID, count/render-duration buckets, interaction type, error category, and layout-duration bucket. Never emit entity IDs/names, series/topic/table names, incident IDs, raw values, query text, tenant/environment IDs, or tooltip content. Accessible alternatives follow the same bounded-field contract. Synthetic fixtures are test-only and the visualization contract check rejects fixture imports from production modules.
