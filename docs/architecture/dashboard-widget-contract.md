# Dashboard widget contract

Each registered widget declares stable type, display name, capability and team, permission, provider, supported ranges/filters, row bound, refresh policy, size bounds, accessible alternative, state messages, canonical drill-down and investigation support. Permission and capability availability are checked before provider invocation. Unknown types are rejected. Widgets support loading, loaded, empty, partial, stale, missing, unavailable, permission denied, not configured, timeout, rate limited and error without translating absence into zero or health.
