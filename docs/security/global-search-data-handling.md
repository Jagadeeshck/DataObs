# Global search data handling

Query text, tokens, result identifiers, labels, URLs, tenant/user IDs and raw errors are prohibited in telemetry. Queries remain React memory only and are not placed in URLs, local/session storage, recents, logs or screenshots. Allowed fields are low-cardinality event/category/count/length/duration buckets, provider IDs and entity types. Backend authorisation remains authoritative; unauthorised providers are never called. Results are never reused after context change.
