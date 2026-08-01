# Console Quick Find

Quick Find opens by button, `/`, Ctrl+K, or Cmd+K outside editable controls. It implements dialog/combobox/listbox semantics, arrow navigation, Enter, Escape, result announcements, focus restoration, and route permission filtering. Navigation searches names, capability IDs, aliases, and groups without loading route chunks.

Recent items use bounded `dataobs.console.recent.v1` local storage containing only entity type, safe label, canonical route, timestamp, tenant, and environment. Reads are tenant/environment isolated. Tokens, payloads, comments, credentials, and provider configuration are prohibited.

No audited API provides a uniform bounded, tenant-scoped search contract across assets, streams, clusters, topics, groups, connectors, schemas, pathways, products, monitors, jobs, runs, and incidents. Those entity-search domains are unavailable rather than faked or implemented as unbounded inventory fan-out. Route discovery and scoped recents continue to work.
