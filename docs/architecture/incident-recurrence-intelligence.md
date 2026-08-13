# Incident recurrence intelligence

Recurrence is a directional relationship from an older distinct incident to a newer incident. Displayable similarity starts at 0.30; high similarity starts at 0.72; machine recurrence proposals require 0.82 similarity, 0.65 confidence, and three independent available matching families. Machines create candidates only and never update `Incident.recurrence_of`.

Operators may confirm or reject with actor, timestamp, reason, evidence references, idempotent identity, and optimistic revision. An unchanged rejected relationship is retained and cannot resurface. Relationship identity binds tenant, environment, canonical incident pair, relationship kind, and scoring version.

Failure-signature families derive a scoped stable identity. Membership is stored separately and is idempotent; families do not hold unbounded ID arrays. No transitive merge follows from A~B and B~C. Merged and split management artifacts are excluded from automatic recurrence. One incident's flood occurrence count never represents multiple recurrences.

Confirmed PIR root-cause categories may contribute; hypotheses and incident root-cause candidates may not. Prior resolution and remediation are historical evidence only and never execute automation.
