# Operating Incident Analytics

Projection rebuilds must always specify tenant, environment, date range and a bounded batch size. Compare projection source revision/checkpoint before writes and reject older source state. Treat missing metrics as missing. Timestamp overrides are deferred from v1 because timeline history must not be rewritten and a complete audited authorization flow is required.
