# Incident Analytics

A deterministic per-incident projection combines incident state with durable, ordered events. MTTA is acknowledged minus opened; MTTR is resolved minus opened; close is separate; signal-to-incident is opened minus first observed. Missing timestamps produce `unavailable` and null, never zero. Repeated state segments are summed and reopen count comes from event history.

Organization queries use bounded Elasticsearch aggregations over the projection: date histograms, allowlisted terms, percentiles p50/p90/p95, averages and counts. Responses must include eligible, measured, missing and partial coverage. Tenant and environment come only from trusted request context; raw Elasticsearch DSL is not a browser contract.
