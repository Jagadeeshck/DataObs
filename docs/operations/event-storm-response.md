# Event Storm response

Use `/incidents/event-storms` to inspect state, representative incident, rates/counts, affected topology, suppression count and current notification intent. Review the timeline and bypass reason codes before responding. Correlation is associative, not causal; the member list can be a bounded sample.

Flood control never rejects findings or incidents. A coalesced decision changes notification intent only. Critical and impact bypasses remain visible and must not be hidden. Provider delivery is outside this runtime.

If updates defer, preserve the stable incident/group, run the reconciliation command, check tenant/environment scope and OCC conflicts, and avoid manual Elasticsearch rewrites. A rollback stops flood writers but retains history for replay and audit.
