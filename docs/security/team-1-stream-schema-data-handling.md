# Streaming schema data handling

Raw Avro JSON, Protobuf source, JSON Schema source, defaults, documentation, examples, records, payloads, headers, credentials, and stack traces are prohibited from durable documents, logs, audit events, and telemetry. Schema material is size-checked (256 KiB), parsed in memory, reduced to fingerprints/counts/categories/salted path hashes, then discarded.

Authorization scope comes from `request.state`; tenant and environment are never accepted from compatibility/blast-radius bodies. IDs isolate tenant, environment, and registry. Queries use fixed aliases, allowlisted fields, timeouts, bounded page sizes/history, search-after, and context-bound signed cursors.
