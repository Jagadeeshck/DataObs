# Capacity planning experience architecture

The planning layer consumes persisted, tenant/environment-scoped Part 1 capacity snapshots. It does not recompute headroom, saturation, state, deficits, or partition pressure. Pure planning contracts derive recovery rates, bounded scenarios, and capability-aware recommendations.

`POST /api/v1/streams/{resourceId}/capacity/simulate` accepts only allow-listed bounded numeric fields. Responses are `hypothetical`, `not_observed`, and non-persisted. Recommendations always require human review and prohibit automatic execution. Historical views must read forecasts and recommendations recorded at time T rather than recomputing with current limits.

Pathway overlays may show capacity state and downstream count, but graph position does not prove causality. Business criticality affects ordering only, never capacity mathematics.
