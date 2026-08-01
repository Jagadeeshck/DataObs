# Operating Pathway Explorer

Use **Refresh evidence** to repeat the current bounded URL-backed inventory query. Changing a filter clears its cursor. Partial, stale, empty, unavailable, and error states require investigation; none imply healthy operation.

Pathway SLO definitions use revision ETags. Updates and deletes require `If-Match`; HTTP 412 means another writer changed the definition and the operator must reload before review. Creation uses an explicit review step and creates a disabled draft. Runtime evaluation is not claimed without monitor-result evidence. Mutation requires the deployment's pathway write capability; no automatic remediation exists.

Current limitations: older pathway projections may contain topology identifiers without embedded edge evidence; those edges are shown unavailable until refreshed by the pathway worker. Impact destinations are plain evidence unless a Console route is known. Comparisons operate only on supplied bounded projection windows and are non-causal.
