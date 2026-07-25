# Kafka compatibility matrix

This matrix separates implemented transport support from versions actually validated in CI. A capability is reported
as `available` only after its source probe succeeds; otherwise it is `partial`, `not_configured`, `unsupported`, or
`error`.

| Component | Supported boundary | Validated by this change |
|---|---|---|
| Kafka broker / KRaft | Kafka Admin API; PLAINTEXT for local development, TLS, mTLS, SASL/PLAIN and SCRAM 256/512 | Not run (container gate pending) |
| Python client | `confluent-kafka` declared by the repository | Unit boundary only |
| Kafka Connect | REST inventory and allowlisted restart only | Unit boundary only |
| Schema Registry | REST subjects, versions and compatibility | Unit boundary only |
| OTel Java/Python | Existing messaging semantic attributes | Not run |
| JMX / Elastic metrics | Optional correlation source | Not configured |
| Elasticsearch / Kibana | Target 9.4.2 | Not run |

AWS MSK IAM is unsupported unless an explicit feature flag and compatible official library are installed. Non-Kafka
adapters remain explicitly unimplemented.
