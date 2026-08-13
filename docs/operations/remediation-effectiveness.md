# Remediation effectiveness operations

Projection inputs must be durable fenced execution state, durable verification events and incident lifecycle evidence. Reprojection is idempotent by episode ID and must reject older source revisions. A late verification can legitimately move an inconclusive projection to verified effective. Rebuilds must specify tenant, environment, dates and batch size. Do not treat the intelligence in-memory adapter as recurrence authority; unavailable durable recurrence is recorded as unavailable.
