# Data change gate data handling

CI artifacts are untrusted. Parsing is bounded and rejects SQL/code, secrets, token-like fields, credentials and environment payloads. Only safe dbt metadata and aggregate profiles are accepted; raw records and failing-row samples are prohibited. Tenant/environment come from authenticated server context. CI profiles are comparison-only evidence and never train production baselines. The core has no source-control mutation client.
