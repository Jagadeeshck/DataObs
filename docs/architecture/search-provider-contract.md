# Search provider contract

Providers declare a unique ID, capability, owner, entity types, permission, minimum query length, result maximum, timeout and availability function. Registration is static. The controller checks permission and runtime capability state before invocation. Providers must use typed shared clients, `AbortSignal`, trusted scope, bounded server filters, and canonical route IDs/parameters; raw payloads and errors never enter shared state. Test fixtures must never be registered in production.
