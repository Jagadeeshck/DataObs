# Console navigation data handling

Navigation visibility is permission-aware but is not an access control. Direct routes retain their existing protection and backend authorization. Tenant and environment are selected from authenticated membership, never trusted from the URL. Context switches invalidate request generations and dispatch a cancellation event before stale details return to a safe parent.

Durable shell state is limited to the sidebar collapsed boolean. Navigation telemetry may contain route ID, workspace ID, source, duration bucket, shell mode, and collapse state. It must never contain entity IDs/labels, tenant/environment IDs, search terms, names, or email addresses. Sensitive entity favourites are prohibited; entity recents remain session-scoped and context-keyed.
