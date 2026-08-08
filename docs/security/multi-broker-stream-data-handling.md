# Multi-broker stream data handling

Multi-broker v1 processes metadata, aggregate operational metrics, and trace identifiers. Adapters allowlist typed fields and exclude credentials, tokens, connection strings, policies, arbitrary broker configuration, payloads, bodies, and business message attributes. Tenant and environment originate from authenticated server context. Broker integrations are read-only and message inspection is explicitly out of scope.
