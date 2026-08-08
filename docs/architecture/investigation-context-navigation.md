# Investigation context and navigation

Tenant and environment come only from authenticated product context. The global time range is authoritative and refresh generation cancels stale collection. URL context accepts an allowlisted entity type, bounded entity ID, verified route ID, safe label and same-origin known return pathname. Tenant, environment, search terms and arbitrary query values are rejected. Pins are memory-only, capped at five, and cleared when trusted tenant or environment changes.
