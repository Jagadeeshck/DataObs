# DataObs Scanner Worker

Small testable worker foundation that loads connectors from the registry, validates tasks, obtains leases, emits heartbeats/OTel attributes, applies timeouts, supports deterministic retries, and returns structured scan executions without a live control plane.
