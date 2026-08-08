# Operational dashboard framework

Dashboards are lazy Team 5 presentation/orchestration surfaces. Six immutable templates reference an explicit registry; persisted JSON supplies only known widget types and bounded layout. The runtime inherits trusted product context, global time range and refresh generation, aborts on context changes, and permits independent widget states. Query keys contain provider, time bucket, safe filters and refresh generation; caches are memory-only and cleared on context changes. Limits are 20 widgets, 8 intended concurrent expensive providers, 50 rows per bounded widget, and 30 seconds minimum auto-refresh. Graph libraries are not in the dashboard chunk.

Missing, zero, stale, partial, forecast, impact and confidence remain distinct source concepts. Link-only widgets honestly state that a bounded aggregate adapter is unavailable rather than computing new semantics.
