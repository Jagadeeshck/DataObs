# Asset trust evidence handling

All reads and writes bind tenant and environment in both deterministic document identity and server-side filters.
Not-found responses must not reveal cross-tenant existence. Evidence references contain canonical identifiers,
not raw rows, SQL, secrets, owner labels in telemetry, or provider payloads. API cursors must use the platform
signed-cursor implementation and bind route, scope, filters, sort, and expiry. Logs and metrics must avoid asset,
table, owner, and database labels.
