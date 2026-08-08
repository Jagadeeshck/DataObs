# Dashboard data handling

API evidence remains in React/in-memory request coordination only and is never written to persistent storage or service-worker caches. Saved views contain presentation configuration only. Entity references are allowed only in session storage Watchlists, scoped by a runtime context fingerprint and cleared on context change. Telemetry is allow-listed and excludes custom names, tenant/environment, identifiers/labels, topics/schemas/search, tokens and raw responses. Permission denial prevents transport invocation and clears/replaces evidence with a non-disclosing state.
