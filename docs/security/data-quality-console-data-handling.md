# Data Quality Console data handling

Quality reads require `quality:read`; monitor inventory and Monitor 360 require `monitors:read`. Every repository lookup is tenant/environment scoped, and missing or cross-tenant monitor subresources return 404. Inventory cursors are signed and bound to scope, route, filters and sort.

The UI allowlists target identity fields: asset, field, pathway, pipeline, service, source type, schema, table, columns and timestamp column. It never renders `connection_ref`, credentials, authorization data, secrets, arbitrary SQL, arbitrary target parameters, historical definition documents, internal approval tokens or raw recommendation evidence. Definition history is projected to revision, action, actor, ETag, checksum and occurrence time.

Missing values remain unknown rather than zero. Incident relationships never imply causation. This release exposes no mutation controls.
